"""
Demonstration & Tutorial: AI-Powered Automatic Block Planning System
Complete walkthrough with sample data and visualizations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Import system components
from core_data_models import (
    MaintenanceDefect, OverdueTask, BlockAvailability, TrainSchedule,
    Corridor, CriticalityLevel, MaintenanceStatus, DepartmentType,
    BlockStatus
)
from main_system import RailwayBlockPlannerSystem, create_sample_data
from prioritization_engine import PrioritizationEngine
from block_scheduler import BlockScheduler
from planning_modules import PlanningOrchestrator
from analysis_reporting import (
    ReportGenerator, MetricsCalculator, VisualizationGenerator
)


def generate_realistic_data():
    """Generate realistic sample data for demonstration"""
    
    print("=" * 70)
    print("GENERATING REALISTIC SAMPLE DATA")
    print("=" * 70)
    
    # Create corridors
    corridors = [
        Corridor(
            corridor_id="COR001",
            name="Mumbai-Delhi Main Line",
            source_station="MUMBAI CENTRAL",
            destination_station="NEW DELHI",
            distance_km=1450,
            asset_type="Track",
            department=DepartmentType.ENGINEERING,
            criticality=CriticalityLevel.CRITICAL
        ),
        Corridor(
            corridor_id="COR002",
            name="Howrah-Chennai Line",
            source_station="HOWRAH JN",
            destination_station="CHENNAI CENTRAL",
            distance_km=1680,
            asset_type="OHE",
            department=DepartmentType.TRACTION_DISTRIBUTION,
            criticality=CriticalityLevel.HIGH
        ),
        Corridor(
            corridor_id="COR003",
            name="Lucknow-Agra Line",
            source_station="LUCKNOW JN",
            destination_station="AGRA JN",
            distance_km=380,
            asset_type="Signal",
            department=DepartmentType.SIGNAL_TELECOM,
            criticality=CriticalityLevel.HIGH
        ),
    ]
    
    # Create defects
    defects = [
        # Critical defects
        MaintenanceDefect(
            defect_id="DEF001",
            corridor_id="COR001",
            asset_type="Track",
            defect_type="Rail Fracture",
            department=DepartmentType.ENGINEERING,
            severity=CriticalityLevel.CRITICAL,
            description="Critical rail fracture at km 745.3 - poses safety risk",
            reported_date=datetime.now() - timedelta(days=15),
            estimated_duration_hours=10.0,
            status=MaintenanceStatus.PENDING,
            impact_on_availability=0.95
        ),
        MaintenanceDefect(
            defect_id="DEF002",
            corridor_id="COR002",
            asset_type="OHE",
            defect_type="Cable Deterioration",
            department=DepartmentType.TRACTION_DISTRIBUTION,
            severity=CriticalityLevel.CRITICAL,
            description="OHE cable showing severe wear and tear",
            reported_date=datetime.now() - timedelta(days=12),
            estimated_duration_hours=8.0,
            status=MaintenanceStatus.PENDING,
            impact_on_availability=0.90
        ),
        # High priority defects
        MaintenanceDefect(
            defect_id="DEF003",
            corridor_id="COR001",
            asset_type="Track",
            defect_type="Ballast Deformation",
            department=DepartmentType.ENGINEERING,
            severity=CriticalityLevel.HIGH,
            description="Track ballast showing significant deformation",
            reported_date=datetime.now() - timedelta(days=8),
            estimated_duration_hours=6.0,
            status=MaintenanceStatus.PENDING,
            impact_on_availability=0.65
        ),
        MaintenanceDefect(
            defect_id="DEF004",
            corridor_id="COR003",
            asset_type="Signal",
            defect_type="Signal Controller Malfunction",
            department=DepartmentType.SIGNAL_TELECOM,
            severity=CriticalityLevel.HIGH,
            description="Signal controller at station STA-05 malfunctioning",
            reported_date=datetime.now() - timedelta(days=5),
            estimated_duration_hours=4.0,
            status=MaintenanceStatus.PENDING,
            impact_on_availability=0.75
        ),
        # Medium priority
        MaintenanceDefect(
            defect_id="DEF005",
            corridor_id="COR002",
            asset_type="OHE",
            defect_type="Wire Sagging",
            department=DepartmentType.TRACTION_DISTRIBUTION,
            severity=CriticalityLevel.MEDIUM,
            description="Mild OHE wire sagging at km 890.5",
            reported_date=datetime.now() - timedelta(days=3),
            estimated_duration_hours=3.0,
            status=MaintenanceStatus.PENDING,
            impact_on_availability=0.40
        ),
    ]
    
    # Create overdue tasks
    tasks = [
        OverdueTask(
            task_id="TASK001",
            corridor_id="COR001",
            task_type="Monthly Track Inspection",
            department=DepartmentType.ENGINEERING,
            due_date=datetime.now() - timedelta(days=10),
            estimated_duration_hours=4.0,
            criticality=CriticalityLevel.HIGH,
            frequency="Monthly",
            status=MaintenanceStatus.PENDING
        ),
        OverdueTask(
            task_id="TASK002",
            corridor_id="COR002",
            task_type="Quarterly OHE Maintenance",
            department=DepartmentType.TRACTION_DISTRIBUTION,
            due_date=datetime.now() - timedelta(days=15),
            estimated_duration_hours=5.0,
            criticality=CriticalityLevel.CRITICAL,
            frequency="Quarterly",
            status=MaintenanceStatus.PENDING
        ),
        OverdueTask(
            task_id="TASK003",
            corridor_id="COR003",
            task_type="Routine Signal Check",
            department=DepartmentType.SIGNAL_TELECOM,
            due_date=datetime.now() - timedelta(days=5),
            estimated_duration_hours=3.0,
            criticality=CriticalityLevel.MEDIUM,
            frequency="Weekly",
            status=MaintenanceStatus.PENDING
        ),
    ]
    
    # Create available blocks (from COA)
    blocks = []
    start_date = datetime.now() + timedelta(days=1)
    for i in range(20):
        block_date = start_date + timedelta(days=i // 3)
        blocks.append(
            BlockAvailability(
                corridor_id=f"COR{(i % 3) + 1:03d}",
                start_time=block_date.replace(hour=22, minute=0),
                end_time=block_date.replace(hour=22, minute=0) + timedelta(hours=6 + (i % 4)),
                duration_hours=6 + (i % 4),
                status=BlockStatus.AVAILABLE,
                number_of_trains_affected=5 + (i % 10)
            )
        )
    
    # Create train schedule
    trains = [
        TrainSchedule(
            train_number="12238",
            train_name="Begampura Express",
            source_station="VARANASI",
            destination_station="JAMMU",
            scheduled_departure=datetime.now() + timedelta(days=1, hours=6),
            scheduled_arrival=datetime.now() + timedelta(days=2, hours=8),
            distance_km=1260,
            train_category="Express"
        ),
        TrainSchedule(
            train_number="12301",
            train_name="Rajdhani Express",
            source_station="HOWRAH",
            destination_station="NEW DELHI",
            scheduled_departure=datetime.now() + timedelta(days=1, hours=10),
            scheduled_arrival=datetime.now() + timedelta(days=1, hours=16),
            distance_km=1450,
            train_category="SuperExpress"
        ),
    ]
    
    print(f"✓ Generated {len(defects)} defects")
    print(f"✓ Generated {len(tasks)} overdue tasks")
    print(f"✓ Generated {len(blocks)} available blocks")
    print(f"✓ Generated {len(trains)} train schedules")
    print(f"✓ Generated {len(corridors)} corridors")
    
    return {
        'defects': defects,
        'tasks': tasks,
        'blocks': blocks,
        'trains': trains,
        'corridors': corridors
    }


def run_prioritization_demo(defects, tasks):
    """Demonstrate prioritization engine"""
    print("\n" + "=" * 70)
    print("PRIORITIZATION ENGINE DEMONSTRATION")
    print("=" * 70)
    
    engine = PrioritizationEngine()
    
    # Prioritize defects
    print("\n1. Prioritizing Maintenance Defects...")
    prioritized_defects = engine.prioritize_defects(defects)
    
    print(f"\nTop Defects by Urgency Score:\n")
    print(f"{'Rank':<5} {'Defect ID':<10} {'Type':<25} {'Dept':<25} {'Score':<8}")
    print("-" * 75)
    for i, (defect, score) in enumerate(prioritized_defects, 1):
        print(f"{i:<5} {defect.defect_id:<10} {defect.defect_type:<25} "
              f"{defect.department.value[:24]:<25} {score:<8.2f}")
    
    # Prioritize tasks
    print("\n2. Prioritizing Overdue Tasks...")
    prioritized_tasks = engine.prioritize_overdue_tasks(tasks)
    
    print(f"\nTop Tasks by Urgency Score:\n")
    print(f"{'Rank':<5} {'Task ID':<10} {'Type':<25} {'Criticality':<12} {'Score':<8}")
    print("-" * 75)
    for i, (task, score) in enumerate(prioritized_tasks, 1):
        print(f"{i:<5} {task.task_id:<10} {task.task_type:<25} "
              f"{task.criticality.name:<12} {score:<8.2f}")
    
    return prioritized_defects, prioritized_tasks


def run_block_scheduling_demo(defects, tasks, blocks, trains, corridors):
    """Demonstrate block scheduling"""
    print("\n" + "=" * 70)
    print("BLOCK SCHEDULING OPTIMIZATION DEMONSTRATION")
    print("=" * 70)
    
    engine = PrioritizationEngine()
    scheduler = BlockScheduler(engine)
    
    print("\nScheduling maintenance blocks...")
    scheduled_blocks = scheduler.schedule_blocks(
        defects, tasks, blocks, trains, planning_horizon_days=30
    )
    
    print(f"✓ Scheduled {len(scheduled_blocks)} maintenance blocks\n")
    
    print(f"{'Block ID':<15} {'Corridor':<10} {'Start Date':<15} {'Duration':<10} {'Priority':<12}")
    print("-" * 75)
    for block in scheduled_blocks[:10]:  # Show first 10
        duration = (block.scheduled_end - block.scheduled_start).total_seconds() / 3600
        print(f"{block.block_id[:14]:<15} {block.corridor_id:<10} "
              f"{block.scheduled_start.date():<15} {duration:<10.1f}h {block.priority.name:<12}")
    
    return scheduled_blocks


def run_planning_cycle_demo(sample_data):
    """Demonstrate complete planning cycle"""
    print("\n" + "=" * 70)
    print("COMPLETE PLANNING CYCLE DEMONSTRATION")
    print("=" * 70)
    
    system = RailwayBlockPlannerSystem()
    
    results = system.run_planning_cycle(
        sample_data['defects'],
        sample_data['tasks'],
        sample_data['blocks'],
        sample_data['trains'],
        sample_data['corridors']
    )
    
    # Display results
    weekly_plan = results['weekly_plan']
    monthly_plan = results['monthly_plan']
    
    print("\nWEEKLY PLAN SUMMARY")
    print(f"  Blocks Allocated: {weekly_plan.total_maintenance_blocks}")
    print(f"  Total Duration: {weekly_plan.total_duration_hours:.1f} hours")
    print(f"  Asset Uptime: {weekly_plan.average_asset_uptime*100:.1f}%")
    print(f"  Coordination: {weekly_plan.multi_dept_coordination_efficiency*100:.1f}%")
    
    print("\nMONTHLY PLAN SUMMARY")
    print(f"  Blocks Allocated: {monthly_plan.total_maintenance_blocks}")
    print(f"  Total Duration: {monthly_plan.total_duration_hours:.1f} hours")
    print(f"  Asset Uptime: {monthly_plan.average_asset_uptime*100:.1f}%")
    print(f"  Coordination: {monthly_plan.multi_dept_coordination_efficiency*100:.1f}%")
    
    return results


def run_reporting_demo(results):
    """Demonstrate reporting and visualization"""
    print("\n" + "=" * 70)
    print("REPORTING & VISUALIZATION DEMONSTRATION")
    print("=" * 70)
    
    weekly_plan = results['weekly_plan']
    visualizer = VisualizationGenerator()
    
    # Corridor distribution
    print("\n1. Corridor Distribution:")
    corridor_dist = visualizer.get_corridor_distribution(weekly_plan.allocated_blocks)
    for corridor, count in sorted(corridor_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"  {corridor}: {count} blocks")
    
    # Department workload
    print("\n2. Department Workload Distribution:")
    dept_workload = visualizer.get_department_workload(weekly_plan.allocated_blocks)
    for dept, hours in sorted(dept_workload.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dept}: {hours:.1f} hours")
    
    # Priority distribution
    print("\n3. Priority Distribution:")
    priority_dist = visualizer.get_priority_distribution(weekly_plan.allocated_blocks)
    for priority, count in sorted(priority_dist.items()):
        print(f"  {priority}: {count} blocks")
    
    # Calculate metrics
    calc = MetricsCalculator()
    uptime = calc.calculate_asset_uptime(weekly_plan.allocated_blocks)
    utilization = calc.calculate_block_utilization(weekly_plan.allocated_blocks)
    
    print("\n4. Key Performance Indicators:")
    print(f"  Asset Uptime: {uptime*100:.1f}%")
    print(f"  Block Utilization: {utilization*100:.1f}%")
    print(f"  Multi-Dept Coordination: {weekly_plan.multi_dept_coordination_efficiency*100:.1f}%")


def main():
    """Main demonstration function"""
    
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " AI-POWERED AUTOMATIC BLOCK PLANNING SYSTEM - DEMONSTRATION ".center(68) + "║")
    print("║" + " Indian Railways Maintenance Optimization ".center(68) + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Step 1: Generate data
    print("\n[STEP 1] GENERATING SAMPLE DATA")
    sample_data = generate_realistic_data()
    
    # Step 2: Run prioritization
    print("\n[STEP 2] RUNNING PRIORITIZATION ENGINE")
    prioritized_defects, prioritized_tasks = run_prioritization_demo(
        sample_data['defects'], sample_data['tasks']
    )
    
    # Step 3: Run block scheduling
    print("\n[STEP 3] RUNNING BLOCK SCHEDULING OPTIMIZER")
    scheduled_blocks = run_block_scheduling_demo(
        sample_data['defects'], sample_data['tasks'],
        sample_data['blocks'], sample_data['trains'],
        sample_data['corridors']
    )
    
    # Step 4: Run complete planning cycle
    print("\n[STEP 4] RUNNING COMPLETE PLANNING CYCLE")
    results = run_planning_cycle_demo(sample_data)
    
    # Step 5: Generate reports and visualizations
    print("\n[STEP 5] GENERATING REPORTS & VISUALIZATIONS")
    run_reporting_demo(results)
    
    # Print sample reports
    print("\n" + "=" * 70)
    print("SAMPLE WEEKLY REPORT (excerpt)")
    print("=" * 70)
    report = results['weekly_report']
    print(report[:1500] + "\n... [Report continues] ...\n")
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Export weekly plan to CSV")
    print("2. Share reports with department heads")
    print("3. Distribute block schedules to control offices")
    print("4. Monitor plan execution and update as needed")
    print("\n")


if __name__ == "__main__":
    main()
