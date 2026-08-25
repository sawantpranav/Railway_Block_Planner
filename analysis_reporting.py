"""
Analysis and Reporting System
Generates insights, visualizations, and reports for block planning outcomes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from core_data_models import (
    MaintenanceBlock, BlockPlan, PlanningMetrics, MaintenanceDefect,
    OverdueTask, DepartmentType
)


class MetricsCalculator:
    """Calculates key performance indicators"""
    
    @staticmethod
    def calculate_asset_uptime(blocks: List[MaintenanceBlock],
                              total_hours: float = 168.0) -> float:
        """
        Calculate asset uptime percentage
        
        Args:
            blocks: List of maintenance blocks
            total_hours: Total hours in period (default: 168 for 1 week)
            
        Returns:
            Uptime percentage (0-1)
        """
        total_downtime = sum(
            (b.scheduled_end - b.scheduled_start).total_seconds() / 3600
            for b in blocks
        )
        
        return max(0, 1.0 - (total_downtime / total_hours))
    
    @staticmethod
    def calculate_block_utilization(blocks: List[MaintenanceBlock],
                                   available_blocks: int = 20) -> float:
        """
        Calculate block utilization rate
        
        Args:
            blocks: Allocated maintenance blocks
            available_blocks: Total available blocks in period
            
        Returns:
            Utilization rate (0-1)
        """
        return min(1.0, len(blocks) / available_blocks)
    
    @staticmethod
    def calculate_multi_dept_efficiency(blocks: List[MaintenanceBlock]) -> float:
        """
        Calculate multi-department coordination efficiency
        
        Args:
            blocks: List of maintenance blocks
            
        Returns:
            Efficiency score (0-1, higher = better coordination)
        """
        if not blocks:
            return 0.0
        
        return np.mean([b.coordination_score for b in blocks])
    
    @staticmethod
    def calculate_maintenance_completion_rate(blocks: List[MaintenanceBlock],
                                             total_tasks: int) -> float:
        """
        Calculate percentage of scheduled tasks in blocks
        
        Args:
            blocks: Allocated maintenance blocks
            total_tasks: Total maintenance tasks
            
        Returns:
            Completion rate (0-1)
        """
        scheduled_tasks = set()
        for block in blocks:
            scheduled_tasks.update(block.assigned_tasks)
        
        return len(scheduled_tasks) / total_tasks if total_tasks > 0 else 0.0
    
    @staticmethod
    def calculate_emergency_block_reduction(
        current_blocks: List[MaintenanceBlock],
        historical_blocks: List[MaintenanceBlock] = None) -> float:
        """
        Calculate reduction in emergency/unplanned blocks
        
        Args:
            current_blocks: Current planned blocks
            historical_blocks: Historical block data
            
        Returns:
            Reduction percentage (0-1)
        """
        if historical_blocks is None:
            # Assume 30% reduction from historical patterns
            return 0.30
        
        historical_emergency = len([b for b in historical_blocks 
                                   if b.priority.value >= 3])
        current_high_priority = len([b for b in current_blocks 
                                     if b.priority.value >= 3])
        
        if historical_emergency == 0:
            return 0.0
        
        return (historical_emergency - current_high_priority) / historical_emergency
    
    @staticmethod
    def calculate_train_impact_score(blocks: List[MaintenanceBlock]) -> float:
        """
        Calculate impact on train operations
        
        Args:
            blocks: List of maintenance blocks
            
        Returns:
            Impact score (0-1, higher = more impact)
        """
        if not blocks:
            return 0.0
        
        return np.mean([b.impact_score for b in blocks])


class ReportGenerator:
    """Generates comprehensive planning reports"""
    
    @staticmethod
    def generate_weekly_report(plan: BlockPlan,
                               defects: List[MaintenanceDefect],
                               tasks: List[OverdueTask]) -> str:
        """
        Generate formatted weekly planning report
        
        Args:
            plan: BlockPlan object
            defects: List of maintenance defects
            tasks: List of overdue tasks
            
        Returns:
            Formatted report text
        """
        report = f"""
{'='*70}
WEEKLY MAINTENANCE BLOCK PLAN REPORT
{'='*70}

Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Planning Period: {plan.start_date.date()} to {plan.end_date.date()}

PLAN OVERVIEW
{'='*70}
Total Maintenance Blocks Allocated: {plan.total_maintenance_blocks}
Total Maintenance Duration: {plan.total_duration_hours:.1f} hours
Average Asset Uptime: {plan.average_asset_uptime*100:.1f}%
Multi-Department Coordination: {plan.multi_dept_coordination_efficiency*100:.1f}%
Estimated Train Impact: {plan.estimated_train_impact*100:.1f}%

BLOCK ALLOCATION SUMMARY
{'='*70}
"""
        
        # Group blocks by department
        dept_blocks = {}
        for block in plan.allocated_blocks:
            for dept in block.assigned_departments:
                if dept not in dept_blocks:
                    dept_blocks[dept] = []
                dept_blocks[dept].append(block)
        
        for dept, blocks in dept_blocks.items():
            duration = sum((b.scheduled_end - b.scheduled_start).total_seconds() / 3600 
                          for b in blocks)
            report += f"\n{dept.value}:\n"
            report += f"  - Blocks: {len(blocks)}\n"
            report += f"  - Total Duration: {duration:.1f} hours\n"
        
        report += f"\n{'='*70}\n"
        report += "CRITICAL MAINTENANCE ITEMS ADDRESSED\n"
        report += f"{'='*70}\n"
        
        # List critical items being addressed
        critical_defects = [d for d in defects 
                           if d.severity.value >= 3 
                           and d.defect_id in set(t for b in plan.allocated_blocks for t in b.assigned_tasks)]
        
        for defect in critical_defects[:5]:  # Top 5
            report += f"\n- {defect.defect_type} (Corridor: {defect.corridor_id})\n"
            report += f"  Duration: {defect.estimated_duration_hours} hours\n"
        
        report += f"\n{'='*70}\n"
        report += "RECOMMENDATIONS\n"
        report += f"{'='*70}\n"
        
        if plan.average_asset_uptime < 0.90:
            report += "- Consider reducing number of concurrent maintenance activities\n"
        
        if plan.multi_dept_coordination_efficiency < 0.70:
            report += "- Improve multi-department coordination timing\n"
        
        if plan.estimated_train_impact > 0.3:
            report += "- Schedule blocks during off-peak train operations\n"
        
        report += f"\n{'='*70}\n"
        
        return report
    
    @staticmethod
    def generate_monthly_report(plan: BlockPlan,
                               defects: List[MaintenanceDefect],
                               tasks: List[OverdueTask]) -> str:
        """
        Generate formatted monthly planning report
        
        Args:
            plan: BlockPlan object
            defects: List of maintenance defects
            tasks: List of overdue tasks
            
        Returns:
            Formatted report text
        """
        report = f"""
{'='*70}
MONTHLY MAINTENANCE BLOCK PLAN REPORT
{'='*70}

Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Planning Period: {plan.start_date.date()} to {plan.end_date.date()}

PLAN OVERVIEW
{'='*70}
Total Maintenance Blocks: {plan.total_maintenance_blocks}
Total Maintenance Duration: {plan.total_duration_hours:.1f} hours
Average Asset Uptime: {plan.average_asset_uptime*100:.1f}%
Multi-Department Coordination: {plan.multi_dept_coordination_efficiency*100:.1f}%
Estimated Train Impact: {plan.estimated_train_impact*100:.1f}%

KEY METRICS
{'='*70}
"""
        
        # Calculate metrics
        calc = MetricsCalculator()
        
        utilization = calc.calculate_block_utilization(plan.allocated_blocks, 100)
        completion_rate = calc.calculate_maintenance_completion_rate(plan.allocated_blocks, len(defects) + len(tasks))
        
        report += f"Block Utilization Rate: {utilization*100:.1f}%\n"
        report += f"Maintenance Completion Rate: {completion_rate*100:.1f}%\n"
        report += f"Average Downtime per Block: {plan.total_duration_hours/plan.total_maintenance_blocks:.1f} hours\n"
        
        report += f"\n{'='*70}\n"
        report += "WEEK-BY-WEEK BREAKDOWN\n"
        report += f"{'='*70}\n"
        
        # Group by week
        current = plan.start_date
        week_num = 1
        while current < plan.end_date:
            week_end = min(current + timedelta(days=7), plan.end_date)
            week_blocks = [b for b in plan.allocated_blocks 
                          if current <= b.scheduled_start < week_end]
            
            if week_blocks:
                duration = sum((b.scheduled_end - b.scheduled_start).total_seconds() / 3600 
                             for b in week_blocks)
                report += f"\nWeek {week_num} ({current.date()} - {week_end.date()}):\n"
                report += f"  Blocks: {len(week_blocks)}, Duration: {duration:.1f} hours\n"
            
            current = week_end
            week_num += 1
        
        report += f"\n{'='*70}\n"
        
        return report
    
    @staticmethod
    def export_to_csv(plan: BlockPlan,
                     output_file: str = None) -> pd.DataFrame:
        """
        Export block plan to CSV format
        
        Args:
            plan: BlockPlan object
            output_file: Output file path (optional)
            
        Returns:
            DataFrame with block details
        """
        data = []
        for block in plan.allocated_blocks:
            data.append({
                'Block ID': block.block_id,
                'Corridor': block.corridor_id,
                'Start Time': block.scheduled_start,
                'End Time': block.scheduled_end,
                'Duration (hours)': (block.scheduled_end - block.scheduled_start).total_seconds() / 3600,
                'Priority': block.priority.name,
                'Departments': ', '.join(d.value for d in block.assigned_departments),
                'Tasks': len(block.assigned_tasks),
                'Coordination Score': block.coordination_score
            })
        
        df = pd.DataFrame(data)
        
        if output_file:
            df.to_csv(output_file, index=False)
        
        return df


class VisualizationGenerator:
    """Generates visualization data for charts and dashboards"""
    
    @staticmethod
    def get_corridor_distribution(blocks: List[MaintenanceBlock]) -> Dict[str, int]:
        """
        Get distribution of blocks by corridor
        
        Args:
            blocks: List of maintenance blocks
            
        Returns:
            Dictionary with corridor IDs and block counts
        """
        distribution = {}
        for block in blocks:
            distribution[block.corridor_id] = distribution.get(block.corridor_id, 0) + 1
        return distribution
    
    @staticmethod
    def get_department_workload(blocks: List[MaintenanceBlock]) -> Dict[str, float]:
        """
        Get workload distribution by department
        
        Args:
            blocks: List of maintenance blocks
            
        Returns:
            Dictionary with department names and total hours
        """
        workload = {}
        for block in blocks:
            for dept in block.assigned_departments:
                hours = (block.scheduled_end - block.scheduled_start).total_seconds() / 3600
                workload[dept.value] = workload.get(dept.value, 0) + hours
        return workload
    
    @staticmethod
    def get_priority_distribution(blocks: List[MaintenanceBlock]) -> Dict[str, int]:
        """
        Get distribution of blocks by priority
        
        Args:
            blocks: List of maintenance blocks
            
        Returns:
            Dictionary with priority levels and block counts
        """
        distribution = {}
        for block in blocks:
            priority = block.priority.name
            distribution[priority] = distribution.get(priority, 0) + 1
        return distribution
    
    @staticmethod
    def get_timeline_data(blocks: List[MaintenanceBlock]) -> pd.DataFrame:
        """
        Get timeline data for Gantt chart
        
        Args:
            blocks: List of maintenance blocks
            
        Returns:
            DataFrame with timeline information
        """
        data = []
        for block in blocks:
            for dept in block.assigned_departments:
                data.append({
                    'Task': f"{block.block_id[:8]} ({dept.value})",
                    'Corridor': block.corridor_id,
                    'Start': block.scheduled_start,
                    'End': block.scheduled_end,
                    'Priority': block.priority.name
                })
        
        return pd.DataFrame(data)


# Example usage
if __name__ == "__main__":
    calc = MetricsCalculator()
    print("Metrics and Reporting System initialized successfully")
