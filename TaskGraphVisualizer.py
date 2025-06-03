import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Tuple
from Task import Task

class TaskGraphVisualizer:
    """Class for creating visualizations of Task state information"""
    
    def __init__(self):
        """Initialize the visualizer with color schemes"""
        self.color_scheme = {
            'default': '#3B82F6',  # Blue
            'medium': '#F97316',   # Orange (2-4 transitions)
            'high': '#EF4444',     # Red (5-8 transitions)
            'critical': '#000000'  # Black (9+ transitions)
        }
        
        # Define colors for different states
        self.state_colors = {
            'New': '#E5E7EB',          # Light gray
            'Active': '#3B82F6',       # Blue
            'Code Review': '#F59E0B',  # Amber
            'Resolved': '#10B981',     # Green
            'Closed': '#6B7280'        # Gray
        }
    
    def get_bar_color(self, transition_count: int) -> str:
        """
        Get color based on transition count
        
        Args:
            transition_count: Number of transitions to the state
            
        Returns:
            Color code string
        """
        if transition_count >= 9:
            return self.color_scheme['critical']
        elif transition_count >= 5:
            return self.color_scheme['high']
        elif transition_count >= 2:
            return self.color_scheme['medium']
        else:
            return self.color_scheme['default']
    
    def prepare_chart_data(self, task: Task) -> Tuple[List[str], List[float], List[int], List[str]]:
        """
        Prepare data for charting from Task object
        
        Args:
            task: Task object with state_info property
            
        Returns:
            Tuple of (state_names, durations, counts, colors)
        """
        state_names = []
        durations = []
        counts = []
        colors = []
        
        for state_name, info in task.state_info.items():
            state_names.append(state_name)
            durations.append(int(round(info['total_time'])))
            counts.append(info['count'])
            colors.append(self.get_bar_color(info['count']))
        
        print(durations)
        return state_names, durations, counts, colors
    
    
    def create_state_duration_chart(self, task: Task, save_path: str = None, show_plot: bool = True) -> plt.Figure:
        """
        Create a bar chart showing time spent in each state
        
        Args:
            task: Task object to visualize
            save_path: Optional path to save the chart
            show_plot: Whether to display the plot
            
        Returns:
            matplotlib Figure object
        """
        state_names, durations, counts, colors = self.prepare_chart_data(task)
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(9, 6))
        
        # Create bars with different colors
        bars = ax.bar(state_names, durations, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        
        # Customize the chart
        ax.set_xlabel('State', fontsize=12, fontweight='bold')
        ax.set_ylabel('Duration (Days)', fontsize=12, fontweight='bold')
        ax.set_title(f'Task {task.id}: Time Spent in Each State\n{task.title}', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on top of bars
        for bar, duration, count in zip(bars, durations, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{duration}d\n({count}x)',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add grid for better readability
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        # Create custom legend for color coding
        legend_elements = [
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['default'], label='1 transition'),
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['medium'], label='2-4 transitions'),
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['high'], label='5-8 transitions'),
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['critical'], label='9+ transitions')
        ]
        ax.legend(handles=legend_elements, loc='upper right', title='Transition Count')
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Chart saved to: {save_path}")
        
        # Show plot if requested
        if show_plot:
            plt.show()
        
        return fig
    
    def _get_color_description(self, count: int) -> str:
        """Get color description based on transition count"""
        if count >= 9:
            return "Black"
        elif count >= 5:
            return "Red"
        elif count >= 2:
            return "Orange"
        else:
            return "Blue"
    
    def create_stacked_state_comparison_by_task(self, tasks: List[Task], save_path: str = None, show_plot: bool = True):
        """
        Create a stacked bar chart with Task IDs on X-axis and stacked states showing time duration.
        
        X-axis: Task IDs
        Y-axis: Duration (Days)
        Stacks: Different states (New, Active, Code Review, Resolved, Closed)

        Args:
            tasks: List of Task objects
            save_path: Optional path to save the chart
            show_plot: Whether to display the plot
        """
        if not tasks:
            print("No tasks provided for comparison")
            return

        # Define the order of states for consistent stacking
        state_order = ['New', 'Active', 'Code Review', 'Resolved', 'Closed']
        
        # Get all states that actually exist in the tasks
        all_found_states = {state for task in tasks for state in task.state_info}
        ordered_states = [state for state in state_order if state in all_found_states]
        
        # Add any additional states not in our predefined order
        additional_states = [state for state in all_found_states if state not in state_order]
        ordered_states.extend(additional_states)

        # Prepare data
        task_ids = [str(task.id) for task in tasks]
        
        # Create a matrix: rows = states, columns = tasks
        state_durations = {}
        for state in reversed(ordered_states):
            state_durations[state] = []
            for task in tasks:
                info = task.state_info.get(state)
                duration = int(round(info['total_time'])) if info else 0
                state_durations[state].append(duration)

        # Create the plot
        fig, ax = plt.subplots(figsize=(max(9, len(tasks) * 0.7), 6))
        
        # Initialize bottom array for stacking
        bottom = np.zeros(len(tasks))
        
        # Create stacked bars
        bars = []
        for state in reversed(ordered_states):
            durations = state_durations[state]
            color = self.state_colors.get(state, '#8B5CF6')  # Default purple if state not defined
            
            bar = ax.bar(task_ids, durations, bottom=bottom, 
                        label=state, color=color, 
                        edgecolor='black', linewidth=0.5, alpha=0.8)
            bars.append(bar)
            bottom += np.array(durations)

        # Customize the chart
        ax.set_xlabel('Task ID', fontsize=12, fontweight='bold')
        ax.set_ylabel('Duration (Days)', fontsize=12, fontweight='bold')
        ax.set_title('Time Spent in Each State by Task', fontsize=14, fontweight='bold')
        
        # Add legend
        ax.legend(title="States", bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Add grid for better readability
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_axisbelow(True)
        
        # Rotate x-axis labels if there are many tasks
        if len(tasks) > 10:
            plt.xticks(rotation=45, ha='right')
        
        # Add total duration labels on top of each bar
        for i, task in enumerate(tasks):
            total_duration = sum(state_durations[state][i] for state in ordered_states)
            if total_duration > 0:
                ax.text(i, total_duration + max(bottom) * 0.01, 
                       f'{total_duration}', 
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Adjust y-axis to prevent label cutoff
        max_total = max(sum(state_durations[state][i] for state in ordered_states) for i in range(len(tasks)))
        ax.set_ylim(0, max_total * 1.1)  # 10% padding above highest stack

        plt.tight_layout()

        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Stacked state chart saved to: {save_path}")

        # Show plot if requested
        if show_plot:
            plt.show()

        return fig
    
    def visualize_task(self, task: Task, save_path: str = None, show_summary: bool = True, show_chart: bool = True):
        """
        Complete visualization of a task (summary + chart)
        
        Args:
            task: Task object to visualize
            save_path: Optional path to save the chart
            show_summary: Whether to print the summary table
            show_chart: Whether to show the chart
        """
        if show_summary:
            self.print_state_summary_table(task)
        
        if show_chart:
            return self.create_state_duration_chart(task, save_path=save_path, show_plot=show_chart)
        
        return None