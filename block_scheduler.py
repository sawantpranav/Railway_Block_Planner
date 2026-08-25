"""
Block Scheduling Optimizer
Optimizes maintenance block scheduling to maximize asset availability
Uses constraint satisfaction and optimization algorithms
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Set
from core_data_models import (
    MaintenanceDefect, OverdueTask, MaintenanceBlock, BlockAvailability,
    Corridor, BlockPriority, BlockStatus, DepartmentType, MaintenanceStatus,
    TrainSchedule, GoodsTrainForecast
)
from prioritization_engine import PrioritizationEngine


class ConstraintChecker:
    """Validates scheduling constraints"""
    
    @staticmethod
    def check_block_availability(block: BlockAvailability, 
                                 required_duration: float) -> bool:
        """
        Check if block has sufficient duration
        
        Args:
            block: BlockAvailability object
            required_duration: Required duration in hours
            
        Returns:
            True if block is available and has sufficient duration
        """
        if block.status != BlockStatus.AVAILABLE:
            return False
        
        available_hours = (block.end_time - block.start_time).total_seconds() / 3600
        return available_hours >= required_duration
    
    @staticmethod
    def check_multi_department_conflict(departments: Set[DepartmentType]) -> float:
        """
        Calculate coordination complexity for multiple departments
        
        Args:
            departments: Set of departments involved
            
        Returns:
            Coordination score (0-1, higher = more complex)
        """
        # More departments = higher coordination complexity
        complexity_map = {1: 0.1, 2: 0.4, 3: 0.7}
        num_depts = len(departments)
        return complexity_map.get(num_depts, 0.9)
    
    @staticmethod
    def check_train_impact(block: BlockAvailability,
                          train_schedule: List[TrainSchedule]) -> Tuple[int, float]:
        """
        Calculate impact of block on train operations
        
        Args:
            block: BlockAvailability object
            train_schedule: List of trains affected
            
        Returns:
            Tuple of (number_of_trains_affected, total_delay_potential_minutes)
        """
        affected_trains = []
        total_delay = 0.0
        
        for train in train_schedule:
            # Check if train passes through corridor during block
            train_start = train.scheduled_departure
            train_end = train.scheduled_arrival
            
            # Trains overlap with block if they intersect in time
            if train_start <= block.end_time and train_end >= block.start_time:
                affected_trains.append(train.train_number)
                # Estimate delay based on block duration
                total_delay += (block.duration_hours * 60) * 0.3  # 30% of block time as delay
        
        return len(affected_trains), total_delay
    
    @staticmethod
    def check_dependency_satisfaction(task_id: str,
                                     scheduled_tasks: Dict[str, datetime],
                                     dependencies: Dict[str, List[str]]) -> bool:
        """
        Check if task dependencies are satisfied
        
        Args:
            task_id: Task to check
            scheduled_tasks: Dictionary of scheduled task times
            dependencies: Task dependencies mapping
            
        Returns:
            True if all dependencies are already scheduled
        """
        if task_id not in dependencies:
            return True
        
        for dep_id in dependencies[task_id]:
            if dep_id not in scheduled_tasks:
                return False
        
        return True


class BlockScheduler:
    """Main block scheduling optimizer"""
    
    def __init__(self, 
                 prioritization_engine: PrioritizationEngine = None,
                 max_concurrent_corridors: int = 3):
        """
        Initialize block scheduler
        
        Args:
            prioritization_engine: PrioritizationEngine instance
            max_concurrent_corridors: Maximum concurrent maintenance corridors
        """
        self.prioritization_engine = prioritization_engine or PrioritizationEngine()
        self.max_concurrent_corridors = max_concurrent_corridors
        self.constraint_checker = ConstraintChecker()
    
    def schedule_blocks(self,
                       defects: List[MaintenanceDefect],
                       tasks: List[OverdueTask],
                       available_blocks: List[BlockAvailability],
                       train_schedule: List[TrainSchedule],
                       planning_horizon_days: int = 30) -> List[MaintenanceBlock]:
        """
        Schedule maintenance blocks optimally
        
        Args:
            defects: List of maintenance defects
            tasks: List of overdue tasks
            available_blocks: List of available blocks from COA
            train_schedule: List of train schedules
            planning_horizon_days: Planning window in days
            
        Returns:
            List of scheduled MaintenanceBlock objects
        """
        scheduled_blocks = []
        
        # Combine and prioritize all maintenance items
        all_items = []
        
        # Add defects with their urgency scores
        for defect in defects:
            score = self.prioritization_engine.urgency_scorer.score_defect(defect)
            all_items.append(('defect', defect, score))
        
        # Add overdue tasks with their urgency scores
        for task in tasks:
            score = self.prioritization_engine.urgency_scorer.score_overdue_task(task)
            all_items.append(('task', task, score))
        
        # Sort by urgency score (descending)
        all_items.sort(key=lambda x: x[2], reverse=True)
        
        # Allocate blocks to items
        used_blocks = set()
        allocated_items = []
        
        for item_type, item, urgency_score in all_items:
            # Find best available block for this item
            best_block = self._find_best_block(
                item, item_type, available_blocks, used_blocks, train_schedule
            )
            
            if best_block:
                # Create maintenance block
                if item_type == 'defect':
                    maint_block = self._create_block_for_defect(
                        item, best_block, urgency_score, train_schedule
                    )
                else:
                    maint_block = self._create_block_for_task(
                        item, best_block, urgency_score, train_schedule
                    )
                
                scheduled_blocks.append(maint_block)
                used_blocks.add(best_block.block_id)
                allocated_items.append(item)
        
        return scheduled_blocks
    
    def _find_best_block(self,
                        item,
                        item_type: str,
                        available_blocks: List[BlockAvailability],
                        used_blocks: Set[str],
                        train_schedule: List[TrainSchedule]) -> BlockAvailability:
        """
        Find optimal block for a maintenance item
        """
        required_duration = item.estimated_duration_hours
        best_score = -1
        best_block = None
        
        for block in available_blocks:
            # Skip if already used
            if block.block_id in used_blocks:
                continue
            
            # Check basic constraints
            if not self.constraint_checker.check_block_availability(block, required_duration):
                continue
            
            # Calculate score (prefer early scheduling, minimal train impact)
            time_score = 1.0 / (1.0 + (block.start_time - datetime.now()).days)
            
            # Check train impact
            num_trains, delay = self.constraint_checker.check_train_impact(block, train_schedule)
            impact_score = 1.0 / (1.0 + num_trains)
            
            # Combined score
            score = (time_score * 0.5) + (impact_score * 0.5)
            
            if score > best_score:
                best_score = score
                best_block = block
        
        return best_block
    
    def _create_block_for_defect(self,
                                defect: MaintenanceDefect,
                                block: BlockAvailability,
                                urgency_score: float,
                                train_schedule: List[TrainSchedule]) -> MaintenanceBlock:
        """
        Create MaintenanceBlock for a defect
        """
        # Determine block priority
        priority = self.prioritization_engine.assign_block_priority(urgency_score)
        
        # Calculate train impact
        num_trains, delay = self.constraint_checker.check_train_impact(block, train_schedule)
        
        maint_block = MaintenanceBlock(
            corridor_id=defect.corridor_id,
            assigned_tasks=[defect.defect_id],
            assigned_departments={defect.department},
            scheduled_start=block.start_time,
            scheduled_end=block.end_time,
            priority=priority,
            status=BlockStatus.ALLOCATED,
            expected_completion_rate=0.85,
            coordination_score=0.1,  # Single department
            impact_score=len(train_schedule) * 0.1  # Normalized impact
        )
        
        return maint_block
    
    def _create_block_for_task(self,
                              task: OverdueTask,
                              block: BlockAvailability,
                              urgency_score: float,
                              train_schedule: List[TrainSchedule]) -> MaintenanceBlock:
        """
        Create MaintenanceBlock for an overdue task
        """
        # Determine block priority
        priority = self.prioritization_engine.assign_block_priority(urgency_score)
        
        maint_block = MaintenanceBlock(
            corridor_id=task.corridor_id,
            assigned_tasks=[task.task_id],
            assigned_departments={task.department},
            scheduled_start=block.start_time,
            scheduled_end=block.end_time,
            priority=priority,
            status=BlockStatus.ALLOCATED,
            expected_completion_rate=0.90,  # Overdue tasks more predictable
            coordination_score=0.1
        )
        
        return maint_block
    
    def optimize_multi_department_blocks(self,
                                        scheduled_blocks: List[MaintenanceBlock],
                                        defects: List[MaintenanceDefect],
                                        tasks: List[OverdueTask]) -> List[MaintenanceBlock]:
        """
        Optimize blocks for multi-department coordination
        
        Combines tasks from different departments that can be done in same time window
        
        Args:
            scheduled_blocks: Initially scheduled blocks
            defects: All defects
            tasks: All overdue tasks
            
        Returns:
            Optimized block list with better coordination
        """
        # Group blocks by corridor and time window
        corridor_time_blocks = {}
        
        for block in scheduled_blocks:
            key = (block.corridor_id, block.scheduled_start.date())
            if key not in corridor_time_blocks:
                corridor_time_blocks[key] = []
            corridor_time_blocks[key].append(block)
        
        # Merge overlapping blocks from different departments
        optimized_blocks = []
        processed = set()
        
        for key, blocks in corridor_time_blocks.items():
            if len(blocks) > 1:
                # Merge blocks
                merged_block = self._merge_blocks(blocks, defects, tasks)
                optimized_blocks.append(merged_block)
                for b in blocks:
                    processed.add(b.block_id)
            else:
                if blocks[0].block_id not in processed:
                    optimized_blocks.append(blocks[0])
                    processed.add(blocks[0].block_id)
        
        return optimized_blocks
    
    def _merge_blocks(self,
                     blocks: List[MaintenanceBlock],
                     defects: List[MaintenanceDefect],
                     tasks: List[OverdueTask]) -> MaintenanceBlock:
        """
        Merge multiple blocks into one coordinated block
        """
        # Combine all tasks and departments
        all_tasks = set()
        all_depts = set()
        earliest_start = blocks[0].scheduled_start
        latest_end = blocks[0].scheduled_end
        highest_priority = max(
            (block.priority for block in blocks),
            key=lambda priority: priority.value
        )
        
        for block in blocks:
            all_tasks.update(block.assigned_tasks)
            all_depts.update(block.assigned_departments)
            if block.scheduled_start < earliest_start:
                earliest_start = block.scheduled_start
            if block.scheduled_end > latest_end:
                latest_end = block.scheduled_end
            if block.priority.value > highest_priority.value:
                highest_priority = block.priority
        
        # Calculate coordination score for multiple departments
        coord_score = 1.0 - ConstraintChecker.check_multi_department_conflict(all_depts)
        
        merged_block = MaintenanceBlock(
            corridor_id=blocks[0].corridor_id,
            assigned_tasks=list(all_tasks),
            assigned_departments=all_depts,
            scheduled_start=earliest_start,
            scheduled_end=latest_end,
            priority=highest_priority,
            status=BlockStatus.ALLOCATED,
            expected_completion_rate=0.80,  # Slightly lower for merged blocks
            coordination_score=coord_score
        )
        
        return merged_block


# Example usage
if __name__ == "__main__":
    from prioritization_engine import PrioritizationEngine
    
    # Create scheduler
    engine = PrioritizationEngine()
    scheduler = BlockScheduler(engine)
    
    print("Block Scheduler initialized successfully")
