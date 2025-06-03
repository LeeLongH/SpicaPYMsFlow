import requests
import json
from typing import List, Dict, Optional
import base64
from datetime import datetime
import re
import urllib.parse


class Task:
    """Represents a single Azure DevOps work item/task"""
    
    def __init__(self, task_id: int, analyzer):
        self.id = task_id
        self.analyzer = analyzer
        self._details = None
        self._resolved_count = None
        self._updates = None
        self._cycle_time = None
        self._lead_time = None
        self._state_info = None

    @property
    def cycle_time(self) -> Optional[float]:
        """Get cycle time in days (from first active state to last closed state)"""
        if self._cycle_time is None:
            self._cycle_time = self.analyzer.calculate_cycle_time(self.id)
            if self._cycle_time is not None:
                self._cycle_time = round(self._cycle_time)
        return self._cycle_time
    
    @property
    def lead_time(self) -> Optional[float]:
        """Get lead time in days (from creation to last closed state)"""
        if self._lead_time is None:
            self._lead_time = self.analyzer.calculate_lead_time(self.id)
            if self._lead_time is not None:
                self._lead_time = round(self._lead_time)
        return self._lead_time

    @property
    def state_info(self) -> Dict[str, Dict]:
        """Get state transition information (lazy loaded)
        
        Returns:
            Dict with state names as keys, each containing:
            - count: number of transitions TO this state
            - total_time: total time spent in this state (days)
        """
        if self._state_info is None:
            analysis = self.analyzer.analyze_state_transitions(self.id)
            
            self._state_info = {}
            
            # Get all unique states from both transition counts and time tracking
            all_states = set()
            all_states.update(analysis['transition_count'].keys())
            all_states.update(analysis['time_in_states'].keys())
            
            # Build the state info dictionary
            for state in all_states:
                self._state_info[state] = {
                    'count': analysis['transition_count'].get(state, 0),
                    'total_time': round(analysis['time_in_states'].get(state, 0.0), 2)
                }
        
        return self._state_info

    @property
    def updates(self) -> Dict:
        """Get task updates/history (lazy loaded)"""
        if self._updates is None:
            self._updates = self.analyzer.get_work_item_updates(self.id)
        return self._updates
    
    @property
    def details(self) -> Dict:
        """Get task details (lazy loaded)
            'id'
            'title'
            'type'
            'state'
            'created'
        """
        if self._details is None:
            self._details = self.analyzer.get_work_item_details(self.id)
        return self._details
    
    @property
    def resolved_count(self) -> int:
        """Get number of times this task was resolved (lazy loaded)"""
        if self._resolved_count is None:
            self._resolved_count = self.analyzer.count_resolved_transitions(self.id)
        return self._resolved_count
    
    @property
    def title(self) -> str:
        """Get task title"""
        return self.details.get('title', 'N/A')
    
    @property
    def current_state(self) -> str:
        """Get current state of the task"""
        return self.details.get('state', 'N/A')
    
    @property
    def work_item_type(self) -> str:
        """Get work item type"""
        return self.details.get('type', 'N/A')
    
    @property
    def created_date(self) -> str:
        """Get creation date"""
        return self.details.get('created', 'N/A')
    
    # Convenience methods for specific states
    def get_state_count(self, state_name: str) -> int:
        """Get number of transitions to a specific state"""
        return self.state_info.get(state_name, {}).get('count', 0)
    
    def get_state_time(self, state_name: str) -> float:
        """Get total time spent in a specific state (in days)"""
        return self.state_info.get(state_name, {}).get('total_time', 0.0)
    
    def get_state_time_hours(self, state_name: str) -> float:
        """Get total time spent in a specific state (in hours)"""
        return self.get_state_time(state_name) * 24
    
    # Quick access to common states
    @property
    def new_count(self) -> int:
        return self.get_state_count('New')
    
    @property
    def new_time(self) -> float:
        return self.get_state_time('New')
    
    @property
    def active_count(self) -> int:
        return self.get_state_count('Active')
    
    @property
    def active_time(self) -> float:
        return self.get_state_time('Active')
    
    @property
    def code_review_count(self) -> int:
        return self.get_state_count('Code Review')
    
    @property
    def code_review_time(self) -> float:
        return self.get_state_time('Code Review')
    
    @property
    def resolved_time(self) -> float:
        return self.get_state_time('Resolved')
    
    @property
    def closed_count(self) -> int:
        return self.get_state_count('Closed')
    
    @property
    def closed_time(self) -> float:
        return self.get_state_time('Closed')
    
    def print_state_summary(self):
        """Print a summary of all state information"""
        print(f"Task {self.id} - {self.title}")
        print(f"Current state: {self.current_state}")
        print("State Summary:")
        
        for state_name, info in self.state_info.items():
            count = info['count']
            time_days = info['total_time']
            time_hours = time_days * 24
            print(f"  {state_name}: {count} transitions, {time_days} days ({time_hours:.1f} hours)")
        
        print(f"Cycle time: {self.cycle_time} days")
        print(f"Lead time: {self.lead_time} days")
    
    def __str__(self) -> str:
        return f"Task {self.id}: {self.title} (Resolved {self.resolved_count} times)"
    
    def __repr__(self) -> str:
        return f"Task(id={self.id}, title='{self.title}', state='{self.current_state}')"