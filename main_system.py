"""
AI-Powered Automatic Block Planning System
Main entry point and orchestrator
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core_data_models import (
    MaintenanceDefect, OverdueTask, BlockAvailability, TrainSchedule,
    Corridor, BlockPlan, CriticalityLevel, MaintenanceStatus, DepartmentType
)
from prioritization_engine import PrioritizationEngine
from block_scheduler import BlockScheduler
from planning_modules import PlanningOrchestrator
from analysis_reporting import ReportGenerator, MetricsCalculator, VisualizationGenerator


class RailwayBlockPlannerSystem:
    """Main system orchestrating the entire block planning process"""
    
    def __init__(self):
        """Initialize the railway block planning system"""
        self.prioritization_engine = PrioritizationEngine()
        self.scheduler = BlockScheduler(self.prioritization_engine)
        self.planning_orchestrator = PlanningOrchestrator()
        self.report_generator = ReportGenerator()
        self.metrics_calculator = MetricsCalculator()
        self.visualization_generator = VisualizationGenerator()
    
    def integrate_maintenance_data(self,
                                   tms_defects: List[Dict],
                                   smms_defects: List[Dict],
                                   tdms_defects: List[Dict],
                                   overdue_tasks: List[Dict]) -> Dict:
        """
        Integrate maintenance data from multiple systems
        
        Args:
            tms_defects: Defects from Track Management System
            smms_defects: Defects from Signalling Maintenance System
            tdms_defects: Defects from Traction Distribution System
            overdue_tasks: Overdue maintenance tasks
            
        Returns:
            Integrated maintenance data
        """
        all_defects = []
        
        # Process TMS defects (Engineering department)
        for defect in tms_defects:
            maint_defect = MaintenanceDefect(
                defect_id=defect.get('id', ''),
                corridor_id=defect.get('corridor_id', ''),
                asset_type="Track",
                defect_type=defect.get('type', ''),
                department=DepartmentType.ENGINEERING,
                severity=CriticalityLevel(defect.get('severity', 2)),
                description=defect.get('description', ''),
                reported_date=datetime.fromisoformat(defect.get('reported_date', str(datetime.now()))),
                estimated_duration_hours=defect.get('duration_hours', 4.0),
                impact_on_availability=defect.get('impact', 0.5)
            )
            all_defects.append(maint_defect)
        
        # Process SMMS defects (Signal & Telecom)
        for defect in smms_defects:
            maint_defect = MaintenanceDefect(
                defect_id=defect.get('id', ''),
                corridor_id=defect.get('corridor_id', ''),
                asset_type="Signal/Telecom",
                defect_type=defect.get('type', ''),
                department=DepartmentType.SIGNAL_TELECOM,
                severity=CriticalityLevel(defect.get('severity', 2)),
                description=defect.get('description', ''),
                reported_date=datetime.fromisoformat(defect.get('reported_date', str(datetime.now()))),
                estimated_duration_hours=defect.get('duration_hours', 4.0),
                impact_on_availability=defect.get('impact', 0.5)
            )
            all_defects.append(maint_defect)
        
        # Process TDMS defects (Traction Distribution)
        for defect in tdms_defects:
            maint_defect = MaintenanceDefect(
                defect_id=defect.get('id', ''),
                corridor_id=defect.get('corridor_id', ''),
                asset_type="Traction/OHE",
                defect_type=defect.get('type', ''),
                department=DepartmentType.TRACTION_DISTRIBUTION,
                severity=CriticalityLevel(defect.get('severity', 2)),
                description=defect.get('description', ''),
                reported_date=datetime.fromisoformat(defect.get('reported_date', str(datetime.now()))),
                estimated_duration_hours=defect.get('duration_hours', 4.0),
                impact_on_availability=defect.get('impact', 0.5)
            )
            all_defects.append(maint_defect)
        
        # Process overdue tasks
        all_tasks = []
        for task in overdue_tasks:
            maint_task = OverdueTask(
                task_id=task.get('id', ''),
                corridor_id=task.get('corridor_id', ''),
                task_type=task.get('type', ''),
                department=DepartmentType[task.get('department', 'ENGINEERING')],
                due_date=datetime.fromisoformat(task.get('due_date', str(datetime.now()))),
                estimated_duration_hours=task.get('duration_hours', 3.0),
                criticality=CriticalityLevel(task.get('criticality', 2)),
                frequency=task.get('frequency', 'Monthly')
            )
            all_tasks.append(maint_task)
        
        return {
            'defects': all_defects,
            'overdue_tasks': all_tasks,
            'total_defects': len(all_defects),
            'total_tasks': len(all_tasks),
            'integration_status': 'Success'
        }
    
    def run_planning_cycle(self,
                          defects: List[MaintenanceDefect],
                          tasks: List[OverdueTask],
                          available_blocks: List[BlockAvailability],
                          train_schedule: List[TrainSchedule],
                          corridors: List[Corridor]) -> Dict:
        """
        Execute complete planning cycle
        
        Args:
            defects: Maintenance defects
            tasks: Overdue tasks
            available_blocks: Available blocks from COA
            train_schedule: Train schedule data
            corridors: Corridor information
            
        Returns:
            Complete planning results
        """
        print(f"\n{'='*70}")
        print("STARTING AUTOMATIC BLOCK PLANNING CYCLE")
        print(f"{'='*70}")
        print(f"Timestamp: {datetime.now()}")
        print(f"Total Defects: {len(defects)}")
        print(f"Total Overdue Tasks: {len(tasks)}")
        print(f"Available Blocks: {len(available_blocks)}")
        
        # Step 1: Prioritize maintenance items
        print(f"\n[1/4] Prioritizing maintenance items...")
        prioritized_defects = self.prioritization_engine.prioritize_defects(defects, top_n=None)
        prioritized_tasks = self.prioritization_engine.prioritize_overdue_tasks(tasks, top_n=None)
        
        print(f"  - Top 3 Urgent Defects:")
        for defect, score in prioritized_defects[:3]:
            print(f"    • {defect.defect_id}: {defect.defect_type} (Score: {score:.1f})")
        
        # Step 2: Generate planning
        print(f"\n[2/4] Generating integrated weekly and monthly plans...")
        planning_results = self.planning_orchestrator.generate_integrated_plan(
            defects, tasks, available_blocks, train_schedule, corridors
        )
        
        weekly_plan = planning_results['weekly_plan']
        monthly_plan = planning_results['monthly_plan']
        
        print(f"  - Weekly Plan: {len(weekly_plan.allocated_blocks)} blocks allocated")
        print(f"  - Monthly Plan: {len(monthly_plan.allocated_blocks)} blocks allocated")
        
        # Step 3: Generate reports
        print(f"\n[3/4] Generating reports...")
        weekly_report = self.report_generator.generate_weekly_report(
            weekly_plan, defects, tasks
        )
        monthly_report = self.report_generator.generate_monthly_report(
            monthly_plan, defects, tasks
        )
        
        # Step 4: Generate visualizations
        print(f"\n[4/4] Generating visualizations...")
        corridor_dist = self.visualization_generator.get_corridor_distribution(
            weekly_plan.allocated_blocks
        )
        dept_workload = self.visualization_generator.get_department_workload(
            weekly_plan.allocated_blocks
        )
        priority_dist = self.visualization_generator.get_priority_distribution(
            weekly_plan.allocated_blocks
        )
        
        print(f"  - Corridors Involved: {len(corridor_dist)}")
        print(f"  - Departments Involved: {len(dept_workload)}")
        
        print(f"\n{'='*70}")
        print("PLANNING CYCLE COMPLETED SUCCESSFULLY")
        print(f"{'='*70}\n")
        
        return {
            'status': 'Success',
            'timestamp': datetime.now(),
            'weekly_plan': weekly_plan,
            'monthly_plan': monthly_plan,
            'weekly_report': weekly_report,
            'monthly_report': monthly_report,
            'prioritized_defects': prioritized_defects,
            'prioritized_tasks': prioritized_tasks,
            'visualizations': {
                'corridor_distribution': corridor_dist,
                'department_workload': dept_workload,
                'priority_distribution': priority_dist
            }
        }
    
    def get_system_status(self) -> Dict:
        """Get current system status and configuration"""
        return {
            'system_name': 'AI-Powered Automatic Block Planning System',
            'version': '1.0.0',
            'status': 'Operational',
            'last_update': datetime.now(),
            'components': {
                'prioritization_engine': 'Active',
                'block_scheduler': 'Active',
                'planning_orchestrator': 'Active',
                'reporting_system': 'Active'
            }
        }


# Demo function
def create_sample_data() -> Dict:
    """Create sample data for demonstration"""
    
    # Sample defects
    defects = [
        MaintenanceDefect(
            defect_id="DEF001",
            corridor_id="COR001",
            asset_type="Track",
            defect_type="Rail Fracture",
            department=DepartmentType.ENGINEERING,
            severity=CriticalityLevel.CRITICAL,
            reported_date=datetime.now() - timedelta(days=15),
            estimated_duration_hours=8.0,
            impact_on_availability=0.95
        ),
        MaintenanceDefect(
            defect_id="DEF002",
            corridor_id="COR002",
            asset_type="OHE",
            defect_type="Cable Deterioration",
            department=DepartmentType.TRACTION_DISTRIBUTION,
            severity=CriticalityLevel.HIGH,
            reported_date=datetime.now() - timedelta(days=8),
            estimated_duration_hours=6.0,
            impact_on_availability=0.8
        ),
    ]
    
    # Sample tasks
    tasks = [
        OverdueTask(
            task_id="TASK001",
            corridor_id="COR001",
            task_type="Preventive Inspection",
            department=DepartmentType.ENGINEERING,
            due_date=datetime.now() - timedelta(days=5),
            estimated_duration_hours=4.0,
            criticality=CriticalityLevel.HIGH
        ),
    ]
    
    # Sample blocks
    blocks = [
        BlockAvailability(
            corridor_id="COR001",
            start_time=datetime.now() + timedelta(days=2),
            end_time=datetime.now() + timedelta(days=2, hours=8),
            duration_hours=8.0
        ),
        BlockAvailability(
            corridor_id="COR002",
            start_time=datetime.now() + timedelta(days=3),
            end_time=datetime.now() + timedelta(days=3, hours=6),
            duration_hours=6.0
        ),
    ]
    
    return {
        'defects': defects,
        'tasks': tasks,
        'blocks': blocks
    }


if __name__ == "__main__":
    # Initialize system
    system = RailwayBlockPlannerSystem()
    print(f"System Status: {system.get_system_status()}")
    
    # Create sample data
    sample_data = create_sample_data()
    
    print("\nRailway Block Planner System initialized successfully")
