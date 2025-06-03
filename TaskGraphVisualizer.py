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
            durations.append(round(info['total_time'], 2))
            counts.append(info['count'])
            colors.append(self.get_bar_color(info['count']))
        
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
        fig, ax = plt.subplots(figsize=(12, 8))
        
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
    
    def print_state_summary_table(self, task: Task):
        """
        Print a formatted table of state information
        
        Args:
            task: Task object to summarize
        """
        print(f"\n{'='*60}")
        print(f"TASK {task.id} STATE SUMMARY")
        print(f"Title: {task.title}")
        print(f"Current State: {task.current_state}")
        print(f"{'='*60}")
        
        # Table header
        print(f"{'State':<15} {'Days':<8} {'Hours':<8} {'Trans':<6} {'Color':<8}")
        print(f"{'-'*15} {'-'*8} {'-'*8} {'-'*6} {'-'*8}")
        
        total_days = 0
        total_transitions = 0
        
        for state_name, info in task.state_info.items():
            days = info['total_time']
            hours = days * 24
            transitions = info['count']
            color_desc = self._get_color_description(transitions)
            
            total_days += days
            total_transitions += transitions
            
            print(f"{state_name:<15} {days:<8.2f} {hours:<8.1f} {transitions:<6} {color_desc:<8}")
        
        print(f"{'-'*15} {'-'*8} {'-'*8} {'-'*6} {'-'*8}")
        print(f"{'TOTAL':<15} {total_days:<8.2f} {total_days*24:<8.1f} {total_transitions:<6}")
        
        # Additional metrics
        if task.cycle_time:
            print(f"\nCycle Time: {task.cycle_time} days")
        if task.lead_time:
            print(f"Lead Time: {task.lead_time} days")
        
        print(f"{'='*60}\n")
    
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
        Create a stacked bar chart showing how much time different tasks spent in each state.
        
        X-axis: States
        Y-axis: Duration (Days)
        Stacks: Different tasks

        Args:
            tasks: List of Task objects
            save_path: Optional path to save the chart
            show_plot: Whether to display the plot
        """
        if not tasks:
            print("No tasks provided for comparison")
            return

        custom_order = ['New', 'Active', 'Code Review', 'Resolved', 'Closed']
        all_found_states = {state for task in tasks for state in task.state_info}
        all_states = [state for state in custom_order if state in all_found_states]

        task_ids = [str(task.id) for task in tasks]

        # Build data: state -> list of durations per task
        state_data = {state: [] for state in all_states}
        for state in all_states:
            for task in tasks:
                info = task.state_info.get(state)
                duration = round(info['total_time'], 2) if info else 0
                state_data[state].append(duration)

        # Plot
        fig, ax = plt.subplots(figsize=(14, 8))
        bottom = np.zeros(len(all_states))  # one bar per state
        task_colors = plt.cm.get_cmap("tab20", len(tasks))  # distinct colors per task

        for idx, task in enumerate(tasks):
            heights = [state_data[state][idx] for state in all_states]
            ax.bar(all_states, heights, bottom=bottom, label=f'Task {task.id}',
                color=task_colors(idx), edgecolor='black', linewidth=0.5)
            bottom += np.array(heights)

        ax.set_xlabel('State', fontsize=12, fontweight='bold')
        ax.set_ylabel('Total Duration (Days)', fontsize=12, fontweight='bold')
        ax.set_title('State-wise Stacked Duration by Task', fontsize=14, fontweight='bold')
        ax.legend(title="Tasks", bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Stacked state chart saved to: {save_path}")

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