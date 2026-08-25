# AI-Powered Automatic Block Planning System
## Indian Railways - Maintenance Block Optimization

### Project Overview
This system integrates maintenance data from multiple departments (TMS, SMMS, TDMS) with corridor availability data to generate optimized block schedules that maximize asset availability while minimizing downtime.

### Project Structure

```
railway_block_planner/
├── data/
│   ├── maintenance/          # Defect, overdue maintenance data
│   ├── corridors/            # Corridor availability data
│   ├── block_schedules/      # Generated block plans
│   └── reference/            # Station codes, train categories
│
├── core/
│   ├── __init__.py
│   ├── data_models.py        # Data structures (Maintenance, Block, Corridor)
│   ├── data_integration.py   # Integration layer for multiple systems
│   └── validators.py         # Data validation rules
│
├── engine/
│   ├── __init__.py
│   ├── prioritization.py     # ML-based maintenance prioritization
│   ├── urgency_scorer.py     # Criticality and urgency scoring
│   └── impact_analyzer.py    # Impact on asset availability
│
├── optimization/
│   ├── __init__.py
│   ├── block_scheduler.py    # Block scheduling algorithms
│   ├── constraint_solver.py  # Handle multi-department constraints
│   └── resource_optimizer.py # Optimize block duration and timing
│
├── planning/
│   ├── __init__.py
│   ├── weekly_planner.py     # Weekly block planning
│   ├── monthly_planner.py    # Monthly block planning
│   └── plan_generator.py     # Block plan generation
│
├── analysis/
│   ├── __init__.py
│   ├── metrics.py            # KPIs and performance metrics
│   ├── visualizer.py         # Chart and report generation
│   └── report_generator.py   # Weekly/monthly reports
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_maintenance_analysis.ipynb
│   ├── 03_optimization_results.ipynb
│   └── 04_block_planning_demo.ipynb
│
├── config/
│   ├── settings.py           # Configuration parameters
│   └── system_config.yaml    # System configurations
│
├── tests/
│   ├── test_data_models.py
│   ├── test_prioritization.py
│   ├── test_optimization.py
│   └── test_planning.py
│
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

### Key Components

#### 1. Data Integration Layer
- Integrates data from TMS, SMMS, TDMS, COA
- Standardizes maintenance records and block availability
- Handles data cleaning and validation

#### 2. Prioritization Engine
- ML-based maintenance task prioritization
- Scores based on: criticality, urgency, asset availability impact
- Handles multi-department coordination

#### 3. Block Scheduling Optimizer
- Allocates maintenance blocks optimally
- Minimizes asset downtime
- Respects constraints (train schedule, block availability, multi-department tasks)
- Uses optimization algorithms (LP, GA, or heuristics)

#### 4. Planning Modules
- Weekly plans: Short-term scheduling (1-4 weeks)
- Monthly plans: Long-term planning (1-3 months)
- Dynamic plan updates based on new defects/urgencies

#### 5. Analysis & Reporting
- Key metrics: Asset uptime, downtime reduction, plan efficiency
- Weekly/monthly performance reports
- Visualization of block schedules and impact analysis

### System Workflow

```
┌─────────────────────────┐
│  Data Integration       │  (TMS, SMMS, TDMS, COA)
├─────────────────────────┤
│  Maintenance Analysis   │  (Defects, Overdue Tasks)
├─────────────────────────┤
│  Prioritization Engine  │  (ML-based Scoring)
├─────────────────────────┤
│  Block Optimization     │  (Scheduling Algorithm)
├─────────────────────────┤
│  Weekly/Monthly Plans   │  (Multi-horizon Planning)
├─────────────────────────┤
│  Reports & Analysis     │  (KPIs, Dashboards)
└─────────────────────────┘
```

### Key Metrics (KPIs)
- **Asset Uptime %**: Time asset is available for operation
- **Maintenance Completion Rate**: % of scheduled maintenance completed on time
- **Block Utilization %**: Efficient use of available maintenance blocks
- **Average Downtime per Asset**: Reduced downtime per maintenance cycle
- **Multi-department Coordination Score**: Efficiency of coordinated maintenance
- **Emergency Block Reduction**: Decrease in unplanned emergency blocks
- **Train Operation Impact**: Minimized train schedule disruptions

### Technology Stack
- **Python 3.9+**
- **Pandas, NumPy**: Data processing
- **Scikit-learn**: ML models for prioritization
- **Scipy, PuLP, OR-Tools**: Optimization algorithms
- **Matplotlib, Seaborn, Plotly**: Visualization
- **Jupyter**: Interactive analysis
- **FastAPI** (optional): REST API for deployment
