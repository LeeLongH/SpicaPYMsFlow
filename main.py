import requests
import json
from typing import List, Dict, Optional
import base64
from datetime import datetime, timezone
import re
import urllib.parse
from dateutil.parser import isoparse

from Task import Task
from TaskGraphVisualizer import TaskGraphVisualizer


class AzureDevOpsHistoryAnalyzer:
    def __init__(self, organization: str, project: str, personal_access_token: str, tasks_id_query_id: str):
        """
        Initialize the Azure DevOps API client

        Args:
            organization: Your Azure DevOps organization name
            project: Your project name
            personal_access_token: Your PAT for authentication
            tasks_id_query_id: Query ID for getting task IDs
        """
        self.organization = organization
        self.project = project
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis"
        self.tasks_id_query_id = tasks_id_query_id

        # Create basic auth header
        auth_string = f":{personal_access_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }

    def get_work_item_updates(self, work_item_id: int) -> Dict:
        """
        Get all updates/revisions for a specific work item

        Args:
            work_item_id: The ID of the work item

        Returns:
            Dictionary containing the API response with all updates
        """
        url = f"{self.base_url}/wit/workItems/{work_item_id}/updates"
        params = {
            'api-version': '7.0'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching updates for work item {work_item_id}: {e}")
            return {}

    def count_resolved_transitions(self, work_item_id: int) -> int:
        """
        Count how many times a work item has transitioned TO 'Resolved' state

        Args:
            work_item_id: The ID of the work item

        Returns:
            Number of times the item entered 'Resolved' state
        """
        self.updates = self.get_work_item_updates(work_item_id)

        if not self.updates or 'value' not in self.updates:
            return 0

        resolved_count = 0

        for update in self.updates['value']:
            # Check if this update contains field changes AND Look for State field changes
            if 'fields' in update and 'System.State' in update['fields']:
                state_change = update['fields']['System.State']

                # Check if the new value is 'Resolved'
                if 'newValue' in state_change and state_change['newValue'] == 'Resolved':
                    resolved_count += 1

        return resolved_count

    def get_work_item_details(self, work_item_id: int) -> Dict:
        """
        Get basic details about a work item (title, type, current state)

        Args:
            work_item_id: The ID of the work item

        Returns:
            Dictionary with work item details
        """
        url = f"{self.base_url}/wit/workItems/{work_item_id}"
        params = {
            'api-version': '7.0',
            '$expand': 'fields'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            return {
                'id': work_item_id,
                'title': data['fields'].get('System.Title', 'N/A'),
                'type': data['fields'].get('System.WorkItemType', 'N/A'),
                'state': data['fields'].get('System.State', 'N/A'),
                'created': data['fields'].get('System.CreatedDate', 'N/A')
            }
        except requests.exceptions.RequestException as e:
            print(f"Error fetching details for work item {work_item_id}: {e}")
            return {}

    def get_task_ids(self) -> List[int]:
        """
        Get Task IDs from the configured query

        Returns:
            List with Task IDs
        """
        api_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/wiql/{self.tasks_id_query_id}?api-version=6.0'
        response = requests.get(api_url, headers=self.headers)

        task_ids = []

        if response.status_code == 200:
            query_result = response.json()
            print(f"Found {len(query_result.get('workItems', []))} work items")
            
            work_items = query_result.get('workItems', [])
            for item in work_items:
                task_ids.append(item['id'])
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
        
        return task_ids

    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks as Task objects

        Returns:
            List of Task objects
        """
        task_ids = self.get_task_ids()
        return [Task(task_id, self) for task_id in task_ids]

    def calculate_cycle_time(self, work_item_id: int) -> Optional[float]:
        """Calculate cycle time from first active state to last closed state"""
        updates = self.get_work_item_updates(work_item_id)
            
        if not updates or 'value' not in updates:
            return None
        
        first_active_date = None
        last_closed_date = None
        
        for update in updates['value']:
            if 'fields' in update and 'System.State' in update['fields']:
                state_change = update['fields']['System.State']
                changed_date = update.get('revisedDate')
                
                if not changed_date:
                    continue
                
                # Find first transition to Active state
                if ('newValue' in state_change and 
                    state_change['newValue'] == "Active" and 
                    first_active_date is None):
                    first_active_date = changed_date
                
                # Find last transition to Closed state
                if ('newValue' in state_change and 
                    state_change['newValue'] == "Closed"):
                    last_closed_date = changed_date
        
        if first_active_date and last_closed_date:
            try:
                start_date = datetime.fromisoformat(first_active_date.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(last_closed_date.replace('Z', '+00:00'))
                return (end_date - start_date).total_seconds() / 86400
            except ValueError as e:
                print(f"Date parsing error: {e}")
                return None
        
        return None

    def calculate_lead_time(self, work_item_id: int) -> Optional[float]:
        """Calculate lead time from creation date to last closed state"""
        updates = self.get_work_item_updates(work_item_id)
        details = self.get_work_item_details(work_item_id)
        
        if not updates or 'value' not in updates or not details:
            return None
        
        created_date = details.get('created')
        last_closed_date = None
        
        for update in updates['value']:
            if 'fields' in update and 'System.State' in update['fields']:
                state_change = update['fields']['System.State']
                changed_date = update.get('revisedDate')
                
                if not changed_date:
                    continue
                
                # Find last transition to Closed state
                if ('newValue' in state_change and 
                    state_change['newValue'] == "Closed"):
                    last_closed_date = changed_date
        
        if created_date and last_closed_date:
            try:
                start_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(last_closed_date.replace('Z', '+00:00'))
                return (end_date - start_date).total_seconds() / 86400
            except ValueError as e:
                print(f"Date parsing error: {e}")
                return None
        
        return None

    def analyze_state_transitions(self, work_item_id: int) -> Dict:
        """
        Analyze state transitions for a work item, counting transitions and calculating time spent in each state

        Args:
            work_item_id: The ID of the work item

        Returns:
            Dictionary containing:
            - transition_count: dict with state names as keys and transition counts as values
            - time_in_states: dict with state names as keys and total time in days as values
        """
        updates = self.get_work_item_updates(work_item_id)
    
        if not updates or 'value' not in updates:
            return {'transition_count': {}, 'time_in_states': {}}
        
        transition_count = {}
        state_history = []
        now = datetime.now(timezone.utc)

        for update in updates['value']:
            if 'fields' in update and 'System.State' in update['fields']:
                state_change = update['fields']['System.State']

                # Try to get ChangedDate from fields, fallback to revisedDate
                changed_date = (
                    update['fields'].get('System.ChangedDate') or
                    update.get('revisedDate')
                )
                if isinstance(changed_date, dict):
                    changed_date = changed_date.get('newValue')
                else:
                    changed_date = changed_date

                if 'newValue' in state_change and changed_date:
                    new_state = state_change['newValue']
                    try:
                        timestamp = isoparse(changed_date)
                        if timestamp <= now:
                            transition_count[new_state] = transition_count.get(new_state, 0) + 1
                            state_history.append((new_state, timestamp))
                    except Exception:
                        continue

        # Sort by timestamp ascending
        state_history.sort(key=lambda x: x[1])

        # Calculate time spent in each state
        time_in_states = {}
        for i in range(len(state_history)):
            current_state, current_time = state_history[i]
            next_time = state_history[i + 1][1] if i + 1 < len(state_history) else now

            duration_days = max(0, (next_time - current_time).total_seconds() / 86400)
            time_in_states[current_state] = time_in_states.get(current_state, 0) + duration_days

        return {
            'transition_count': transition_count,
            'time_in_states': time_in_states
        }
    

def main():
    PAT = "CQmAK8C3rIW6t1pRJjMe8BiX9BYvy5i5psVSeJRELXUftC98w9I2JQQJ99BEACAAAAAiXuTxAAASAZDOcCsE"

    query_url = "https://dev.azure.com/Spica-International/All%20Hours/_queries/query/fd2005c3-8429-4d1f-a01e-40f2beeb21a7/"
    ORGANIZATION = re.search(r"(?<=dev\.azure\.com/)[^/]+", query_url).group(0)
    PROJECT = urllib.parse.unquote(
        re.search(r"dev\.azure\.com/[^/]+/([^/]+)", query_url).group(1)
    )
    TASKS_ID_QUERY_ID = re.search(r"/query/([a-f0-9\-]{36})", query_url).group(1)

    # Initialize the analyzer
    analyzer = AzureDevOpsHistoryAnalyzer(ORGANIZATION, PROJECT, PAT, TASKS_ID_QUERY_ID)

    # Get all tasks as objects
    tasks = analyzer.get_all_tasks()
    
    # For testing with specific tasks
    #tasks = [Task(47615, analyzer)]

         
    #for i, task in enumerate(tasks):
        #print(f"First task: {task.id} has been resolved {task.resolved_count} times")
        #print(first_task)
        #print(task.cycle_time, task.lead_time)
        #task.print_state_summary()
    
    visualizer = TaskGraphVisualizer()
    visualizer.create_stacked_state_comparison_by_task(tasks[0:], save_path="stacked_tasks_comparison.png")


if __name__ == "__main__":
    main()