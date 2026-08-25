"""
Maintenance Task Prioritization Engine
Uses ML and scoring algorithms to prioritize maintenance based on criticality, urgency, and impact
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from core_data_models import (
    MaintenanceDefect, OverdueTask, Corridor, CriticalityLevel, 
    BlockPriority, DepartmentType
)


class UrgencyScorer:
    """Scores urgency of maintenance tasks based on multiple factors"""
    
    def __init__(self, 
                 criticality_weight: float = 0.35,
                 overdue_weight: float = 0.30,
                 impact_weight: float = 0.25,
                 frequency_weight: float = 0.10):
        """
        Initialize urgency scorer with weights
        
        Args:
            criticality_weight: Weight for severity/criticality (0-1)
            overdue_weight: Weight for overdue days
            impact_weight: Weight for impact on asset availability
            frequency_weight: Weight for maintenance frequency/predictability
        """
        self.criticality_weight = criticality_weight
        self.overdue_weight = overdue_weight
        self.impact_weight = impact_weight
        self.frequency_weight = frequency_weight
    
    def score_defect(self, defect: MaintenanceDefect) -> float:
        """
        Calculate urgency score for a defect (0-100)
        
        Args:
            defect: MaintenanceDefect object
            
        Returns:
            Urgency score (0-100, higher = more urgent)
        """
        # Criticality component
        criticality_score = (defect.severity.value / 4.0) * 100
        
        # Overdue component (days since reported)
        days_since_reported = (datetime.now() - defect.reported_date).days
        overdue_score = min(100, (days_since_reported / 30.0) * 100)  # Normalize over 30 days
        
        # Impact component
        impact_score = defect.impact_on_availability * 100
        
        # Defects have lower frequency weight
        frequency_score = 10
        
        # Calculate weighted urgency
        urgency = (
            self.criticality_weight * criticality_score +
            self.overdue_weight * overdue_score +
            self.impact_weight * impact_score +
            self.frequency_weight * frequency_score
        )
        
        return min(100, urgency)
    
    def score_overdue_task(self, task: OverdueTask) -> float:
        """
        Calculate urgency score for overdue maintenance task (0-100)
        
        Args:
            task: OverdueTask object
            
        Returns:
            Urgency score (0-100, higher = more urgent)
        """
        # Criticality component
        criticality_score = (task.criticality.value / 4.0) * 100
        
        # Overdue days component - higher weight for overdue tasks
        overdue_days = max(0, (datetime.now() - task.due_date).days)
        overdue_score = min(100, (overdue_days / 14.0) * 100)  # Normalize over 14 days
        
        # Impact component
        impact_score = 70  # Overdue tasks have inherent high impact
        
        # Frequency component - periodic tasks need regular completion
        frequency_multiplier = 1.2 if "Monthly" in task.frequency else 1.0
        frequency_score = 20 * frequency_multiplier
        
        # Calculate weighted urgency
        urgency = (
            self.criticality_weight * criticality_score +
            self.overdue_weight * overdue_score +
            self.impact_weight * impact_score +
            self.frequency_weight * frequency_score
        )
        
        return min(100, urgency)


class PrioritizationEngine:
    """Main prioritization engine combining multiple scoring methods"""
    
    def __init__(self):
        self.urgency_scorer = UrgencyScorer()
    
    def prioritize_defects(self, 
                          defects: List[MaintenanceDefect],
                          top_n: int = None) -> List[Tuple[MaintenanceDefect, float]]:
        """
        Prioritize maintenance defects by urgency
        
        Args:
            defects: List of MaintenanceDefect objects
            top_n: Return only top N defects (None = all)
            
        Returns:
            List of (defect, urgency_score) tuples sorted by priority
        """
        scored_defects = [
            (defect, self.urgency_scorer.score_defect(defect))
            for defect in defects
        ]
        
        # Sort by score (descending)
        scored_defects.sort(key=lambda x: x[1], reverse=True)
        
        return scored_defects[:top_n] if top_n else scored_defects
    
    def prioritize_overdue_tasks(self, 
                                 tasks: List[OverdueTask],
                                 top_n: int = None) -> List[Tuple[OverdueTask, float]]:
        """
        Prioritize overdue maintenance tasks
        
        Args:
            tasks: List of OverdueTask objects
            top_n: Return only top N tasks (None = all)
            
        Returns:
            List of (task, urgency_score) tuples sorted by priority
        """
        scored_tasks = [
            (task, self.urgency_scorer.score_overdue_task(task))
            for task in tasks
        ]
        
        # Sort by score (descending)
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        return scored_tasks[:top_n] if top_n else scored_tasks
    
    def assign_block_priority(self, urgency_score: float) -> BlockPriority:
        """
        Assign block priority based on urgency score
        
        Args:
            urgency_score: Score from 0-100
            
        Returns:
            BlockPriority enum value
        """
        if urgency_score >= 80:
            return BlockPriority.EMERGENCY
        elif urgency_score >= 60:
            return BlockPriority.URGENT
        elif urgency_score >= 40:
            return BlockPriority.PRIORITY
        else:
            return BlockPriority.ROUTINE
    
    def group_by_department(self, 
                           defects: List[MaintenanceDefect]) -> Dict[DepartmentType, List[MaintenanceDefect]]:
        """
        Group defects by department for coordinated scheduling
        
        Args:
            defects: List of MaintenanceDefect objects
            
        Returns:
            Dictionary mapping department to list of defects
        """
        grouped = {}
        for dept in DepartmentType:
            grouped[dept] = [d for d in defects if d.department == dept]
        return grouped
    
    def calculate_corridor_urgency(self, 
                                   corridor_id: str,
                                   defects: List[MaintenanceDefect],
                                   tasks: List[OverdueTask]) -> float:
        """
        Calculate overall urgency for a corridor
        
        Args:
            corridor_id: Corridor identifier
            defects: List of defects for this corridor
            tasks: List of overdue tasks for this corridor
            
        Returns:
            Urgency score for the corridor (0-100)
        """
        # Filter by corridor
        corridor_defects = [d for d in defects if d.corridor_id == corridor_id]
        corridor_tasks = [t for t in tasks if t.corridor_id == corridor_id]
        
        if not corridor_defects and not corridor_tasks:
            return 0.0
        
        # Calculate average urgency
        defect_scores = [self.urgency_scorer.score_defect(d) for d in corridor_defects]
        task_scores = [self.urgency_scorer.score_overdue_task(t) for t in corridor_tasks]
        
        all_scores = defect_scores + task_scores
        
        return sum(all_scores) / len(all_scores) if all_scores else 0.0


class DependencyAnalyzer:
    """Analyzes dependencies between maintenance tasks for optimal scheduling"""
    
    def __init__(self):
        self.dependency_graph = {}
    
    def identify_dependencies(self, 
                             defects: List[MaintenanceDefect]) -> Dict[str, List[str]]:
        """
        Identify task dependencies from defect list
        
        Args:
            defects: List of MaintenanceDefect objects
            
        Returns:
            Dictionary mapping defect_id to list of dependency defect_ids
        """
        dependencies = {}
        for defect in defects:
            dependencies[defect.defect_id] = defect.dependencies
        
        self.dependency_graph = dependencies
        return dependencies
    
    def find_independent_tasks(self, 
                              defects: List[MaintenanceDefect]) -> List[MaintenanceDefect]:
        """
        Find tasks with no dependencies for parallel scheduling
        
        Args:
            defects: List of MaintenanceDefect objects
            
        Returns:
            List of independent defects
        """
        return [d for d in defects if not d.dependencies]
    
    def get_critical_path(self, defects: List[MaintenanceDefect]) -> List[str]:
        """
        Identify critical path of dependent tasks
        
        Args:
            defects: List of MaintenanceDefect objects
            
        Returns:
            List of defect IDs in critical path
        """
        # Simplified critical path: longest chain of dependencies
        dependencies = self.identify_dependencies(defects)
        
        # Find root tasks (no dependencies)
        root_tasks = [d for d in defects if not d.dependencies]
        
        # Build paths
        critical_path = []
        for root in root_tasks:
            path = self._build_path(root.defect_id, dependencies)
            if len(path) > len(critical_path):
                critical_path = path
        
        return critical_path
    
    def _build_path(self, task_id: str, dependencies: Dict[str, List[str]], visited=None) -> List[str]:
        """
        Recursively build dependency path
        """
        if visited is None:
            visited = set()
        
        if task_id in visited:
            return []
        
        visited.add(task_id)
        path = [task_id]
        
        # Find tasks that depend on this one
        for task, deps in dependencies.items():
            if task_id in deps and task not in visited:
                path.extend(self._build_path(task, dependencies, visited))
        
        return path


# Example usage and demonstration
if __name__ == "__main__":
    # Create sample data
    sample_defects = [
        MaintenanceDefect(
            defect_id="DEF001",
            corridor_id="COR001",
            asset_type="Track",
            defect_type="Rail Fracture",
            department=DepartmentType.ENGINEERING,
            severity=CriticalityLevel.CRITICAL,
            reported_date=datetime.now() - timedelta(days=10),
            estimated_duration_hours=8.0,
            impact_on_availability=0.9
        ),
        MaintenanceDefect(
            defect_id="DEF002",
            corridor_id="COR001",
            asset_type="Track",
            defect_type="Rail Wear",
            department=DepartmentType.ENGINEERING,
            severity=CriticalityLevel.MEDIUM,
            reported_date=datetime.now() - timedelta(days=3),
            estimated_duration_hours=4.0,
            impact_on_availability=0.4
        ),
    ]
    
    # Initialize engine
    engine = PrioritizationEngine()
    
    # Prioritize defects
    prioritized = engine.prioritize_defects(sample_defects)
    print("Prioritized Defects:")
    for defect, score in prioritized:
        print(f"  {defect.defect_id}: Score={score:.2f}, Type={defect.defect_type}")
