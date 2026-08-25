"""
Core Data Models for Railway Block Planning System
Defines structures for Maintenance, Blocks, Corridors, and Train Schedule
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Set
import uuid


class DepartmentType(Enum):
    """Railway Department Types"""
    ENGINEERING = "Engineering"
    TRACTION_DISTRIBUTION = "Traction Distribution"
    SIGNAL_TELECOM = "Signal & Telecommunication"


class MaintenanceStatus(Enum):
    """Maintenance Task Status"""
    PENDING = "Pending"
    OVERDUE = "Overdue"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class CriticalityLevel(Enum):
    """Maintenance Criticality Levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class BlockStatus(Enum):
    """Block Status"""
    AVAILABLE = "Available"
    ALLOCATED = "Allocated"
    OCCUPIED = "Occupied"
    CANCELLED = "Cancelled"


class BlockPriority(Enum):
    """Block Priority Levels"""
    ROUTINE = 1
    PRIORITY = 2
    URGENT = 3
    EMERGENCY = 4


@dataclass
class Station:
    """Railway Station Information"""
    station_code: str
    station_name: str
    zone: str  # Railway zone
    division: str
    latitude: float
    longitude: float


@dataclass
class Corridor:
    """Railway Corridor/Section Information"""
    corridor_id: str
    name: str
    source_station: str
    destination_station: str
    distance_km: float
    asset_type: str  # Track, OHE, Signal etc.
    department: DepartmentType
    criticality: CriticalityLevel


@dataclass
class MaintenanceDefect:
    """Maintenance Defect Record (from TMS, SMMS, TDMS)"""
    defect_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    corridor_id: str = ""
    asset_type: str = ""  # Track section, Traction equipment, Signal system
    defect_type: str = ""  # Nature of defect
    department: DepartmentType = DepartmentType.ENGINEERING
    severity: CriticalityLevel = CriticalityLevel.MEDIUM
    description: str = ""
    reported_date: datetime = field(default_factory=datetime.now)
    urgency_score: int = 0  # 0-100: Higher = more urgent
    estimated_duration_hours: float = 4.0  # Estimated work duration
    status: MaintenanceStatus = MaintenanceStatus.PENDING
    impact_on_availability: float = 0.5  # 0-1: Impact on asset availability
    dependencies: List[str] = field(default_factory=list)  # Other defect IDs


@dataclass
class OverdueTask:
    """Overdue Maintenance Task"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    corridor_id: str = ""
    task_type: str = ""  # Preventive maintenance, Inspection, etc.
    department: DepartmentType = DepartmentType.ENGINEERING
    due_date: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))
    overdue_days: int = 0
    estimated_duration_hours: float = 3.0
    criticality: CriticalityLevel = CriticalityLevel.MEDIUM
    frequency: str = "Monthly"  # Periodic maintenance frequency
    last_completed: Optional[datetime] = None
    status: MaintenanceStatus = MaintenanceStatus.PENDING


@dataclass
class BlockAvailability:
    """Block Availability Information (from COA - Control Office Application)"""
    block_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    corridor_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=4))
    duration_hours: float = 4.0
    status: BlockStatus = BlockStatus.AVAILABLE
    block_type: str = "Scheduled"  # Scheduled, Unscheduled
    number_of_trains_affected: int = 0
    train_delay_potential: float = 0.0  # Potential delay in minutes
    is_weekend: bool = False
    is_holiday: bool = False


@dataclass
class MaintenanceBlock:
    """Allocated Maintenance Block (Output of Scheduler)"""
    block_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    corridor_id: str = ""
    assigned_tasks: List[str] = field(default_factory=list)  # Task/Defect IDs
    assigned_departments: Set[DepartmentType] = field(default_factory=set)
    scheduled_start: datetime = field(default_factory=datetime.now)
    scheduled_end: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=4))
    priority: BlockPriority = BlockPriority.ROUTINE
    status: BlockStatus = BlockStatus.AVAILABLE
    expected_completion_rate: float = 0.85  # Probability of on-time completion
    coordination_score: float = 0.0  # Multi-department coordination efficiency
    impact_score: float = 0.0  # Impact on train operations
    notes: str = ""


@dataclass
class TrainSchedule:
    """Train Schedule Information (from Train Time Table)"""
    train_number: str
    train_name: str
    source_station: str
    destination_station: str
    scheduled_departure: datetime
    scheduled_arrival: datetime
    distance_km: float
    train_category: str  # Passenger, Freight, etc.
    affected_corridors: List[str] = field(default_factory=list)


@dataclass
class GoodsTrainForecast:
    """Goods Train Forecast (from COA Forecast)"""
    forecast_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    corridor_id: str = ""
    forecast_date: datetime = field(default_factory=datetime.now)
    expected_train_count: int = 0
    expected_traffic_intensity: float = 0.0  # 0-1 scale
    forecast_horizon_days: int = 7
    confidence_level: float = 0.85


@dataclass
class BlockPlan:
    """Weekly or Monthly Block Plan"""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_type: str = "Weekly"  # Weekly or Monthly
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=7))
    allocated_blocks: List[MaintenanceBlock] = field(default_factory=list)
    total_maintenance_blocks: int = 0
    total_duration_hours: float = 0.0
    average_asset_uptime: float = 0.95
    multi_dept_coordination_efficiency: float = 0.0
    estimated_train_impact: float = 0.0
    generated_timestamp: datetime = field(default_factory=datetime.now)
    generated_by: str = "AutoBlockPlanner v1.0"
    notes: str = ""


@dataclass
class PlanningMetrics:
    """Key Performance Indicators for Block Planning"""
    plan_id: str = ""
    asset_uptime_percentage: float = 0.95
    maintenance_completion_rate: float = 0.90
    block_utilization_rate: float = 0.80
    average_downtime_hours: float = 10.0
    multi_dept_coordination_score: float = 0.85
    emergency_block_reduction_pct: float = 0.0
    train_operation_impact_score: float = 0.0
    total_defects_addressed: int = 0
    total_overdue_tasks_cleared: int = 0
    plan_adherence_rate: float = 0.88


# Type aliases for convenience
MaintenanceTaskList = List[MaintenanceDefect]
CorridorList = List[Corridor]
BlockScheduleList = List[MaintenanceBlock]
