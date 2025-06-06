# Multi-Dimensional Budget Variance Report

## Overview
The Multi-Dimensional Budget Variance Report is a comprehensive reporting tool that exclusively uses the flexible_budget app's multi-dimensional budget capabilities. This report provides detailed monthly variance analysis comparing budgeted amounts with actual expenses across multiple dimensions simultaneously.

## Features

### Multi-Dimensional Budget Support
- **Exclusive Multi-Dimensional Focus**: Uses only Multi-Dimensional Budget doctype for comprehensive dimensional analysis
- **Monthly Breakdown**: Displays budget data month-wise based on budget document date ranges
- **Proportional Allocation**: Automatically calculates monthly budget amounts based on budget period duration

### Filtering Capabilities
- **Fiscal Year Range**: Filter by From Fiscal Year and To Fiscal Year for precise period selection
- **Multi-Dimensional Filtering**: Apply multiple dimensional filters simultaneously:
  - **Account Filtering**: Multi-select filter for specific expense/income accounts
  - **Cost Center**: Multi-select filter for cost center analysis
  - **Project**: Multi-select filter for project-based budgeting
  - **Branch**: Multi-select filter for branch-wise analysis
  - **Department**: Multi-select filter for departmental budgeting

### Variance Analysis
- **Budget vs Actual**: Side-by-side comparison of budgeted and actual amounts
- **Monthly Variance**: Month-wise variance calculation (Budget - Actual)
- **Variance Percentage**: Percentage-based variance analysis for each month
- **Utilization Percentage**: Shows budget utilization rate per month
- **Color Coding**: Visual indicators for over-budget (red) and under-budget (green) items

### Multi-Dimensional Display
The report dynamically displays columns for:
- **Budget ID**: Source Multi-Dimensional Budget document
- **Account**: Expense/Income account being analyzed
- **Accounting Dimensions**: All configured accounting dimensions (Cost Center, Project, Branch, Department, etc.)
- **Month**: Monthly breakdown with month name and year
- **Budget/Actual/Variance**: Financial analysis columns

## Usage

### Basic Usage
1. Navigate to **Reports > Multi-Dimensional Budget Variance**
2. Select required filters:
   - Company (required)
   - From Fiscal Year (required)
   - To Fiscal Year (required)
3. Apply optional dimensional filters for focused analysis
4. The report will automatically generate monthly data

### Multi-Dimensional Filtering
- Apply multiple dimensional filters simultaneously for precise analysis
- **Account** filter: Focus on specific expense/income accounts
- **Cost Center** filter: Departmental or divisional analysis
- **Project** filter: Project-based budget tracking
- **Branch** filter: Branch-wise organizational analysis
- **Department** filter: Departmental budget analysis

### Report Features
- **Simplified Interface**: Clean interface focused on multi-dimensional analysis
- **Monthly View**: Data organized by months derived from budget document periods
- **Color-Coded Variance**: Visual variance indicators with conditional formatting
- **Chart Visualization**: Monthly budget vs actual comparison charts
- **Summary Statistics**: Overall budget utilization and variance summary

## Report Columns

### Standard Columns
- **Budget Name**: Name of the Multi-Dimensional Budget document
- **Account**: Chart of accounts being analyzed
- **Month**: Monthly breakdown (e.g., "January 2024")

### Dynamic Dimension Columns
The report automatically includes columns for all configured accounting dimensions:
- Cost Center
- Project  
- Branch
- Department
- Custom accounting dimensions

### Analysis Columns
- **Budget Amount**: Proportionally allocated monthly budget amount
- **Actual Amount**: Actual expenses/income for the month
- **Variance Amount**: Budget minus actual (positive = under budget, negative = over budget)
- **Variance %**: Percentage variance from budget
- **Utilization %**: Percentage of budget utilized

#### Auto Fill Fiscal Year
- Click **Auto Fill Fiscal Year** button to automatically populate the fiscal year based on the selected date range

#### Export with Formatting
- Click **Export with Formatting** to generate an Excel file with proper formatting and color coding

#### Budget Adjustment
- Select rows in the report and use **Create Budget Adjustment** to generate journal entries for budget modifications

## Technical Implementation

### File Structure
```
flexible_budget/flexible_budget/report/multi_dimensional_budget_variance/
├── multi_dimensional_budget_variance.py     # Main Python report logic
├── multi_dimensional_budget_variance.js     # JavaScript frontend enhancements
└── multi_dimensional_budget_variance.json   # Report configuration
```

### Key Functions

#### Python Backend (`multi_dimensional_budget_variance.py`)
- `execute(filters)`: Main report execution function
- `get_multi_dimensional_budget_data()`: Handles flexible_budget app data
- `get_standard_budget_data()`: Handles ERPNext standard budget data
- `get_actual_expenses()`: Calculates actual expenses from GL entries
- `export_to_excel()`: Generates formatted Excel exports
- `create_budget_adjustment()`: Creates journal entries for budget adjustments

#### JavaScript Frontend (`multi_dimensional_budget_variance.js`)
- Filter definitions with dynamic options
- Color coding for variance visualization
- Interactive buttons for fiscal year auto-fill and export
- Budget adjustment dialog functionality

### Integration Points

#### ERPNext Integration
- Uses `erpnext.accounts.utils.get_fiscal_year` for fiscal year calculation
- Integrates with ERPNext's Budget doctype
- Leverages GL Entry for actual expense calculation
- Supports ERPNext's accounting dimensions

#### Flexible Budget App Integration
- Reads multi-dimensional budget configurations
- Supports multiple accounting dimensions
- Handles dimension-specific budget allocations
- Integrates with validation functions from `flexible_budget.utils`

## Data Sources

### Multi-Dimensional Budget Data
- **Multi Dimensional Budget**: Main budget document
- **Multi Dimensional Budget Account**: Account-wise budget allocations
- **Multi Dimensional Budget Account Detail**: Dimension-specific details

### Standard Budget Data
- **Budget**: ERPNext's standard budget document
- **Budget Account**: Account-wise standard budget allocations

### Actual Data
- **GL Entry**: General ledger entries for actual expense calculation
- Filtered by date range, account, and dimensional filters

## Output Format

### Columns
1. **Account**: Account name and code
2. **Cost Center**: Cost center (if applicable)
3. **Dynamic Dimensions**: Additional columns for each active accounting dimension
4. **Budget Amount**: Total budgeted amount for the period
5. **Actual Amount**: Total actual expenses for the period
6. **Variance**: Budget - Actual (positive = under budget, negative = over budget)
7. **Variance %**: Percentage variance ((Budget - Actual) / Budget * 100)

### Summary Statistics
- Total Budget Amount
- Total Actual Amount
- Overall Variance
- Budget Utilization Rate
- Number of over-budget items
- Number of under-budget items

### Chart Visualization
- Bar chart comparing Budget vs Actual amounts
- Visual representation of overall variance
- Color-coded variance indicators

## Permissions
The report is accessible to users with the following roles:
- Accounts Manager
- Accounts User
- Auditor
- System Manager

## Performance Considerations
- Report timeout set to 300 seconds for complex multi-dimensional queries
- Efficient querying with proper indexing on date and account fields
- Pagination support for large datasets
- Optimized GL Entry aggregation queries

## Troubleshooting

### Common Issues
1. **No Data Displayed**: Check if budgets exist for the selected date range and filters
2. **Slow Performance**: Reduce date range or apply more specific filters
3. **Missing Dimensions**: Ensure accounting dimensions are properly configured
4. **Export Errors**: Check file permissions and available disk space

### Error Handling
- Comprehensive validation of input filters
- Graceful handling of missing budget data
- Error logging for debugging purposes
- User-friendly error messages

## Future Enhancements
- Support for budget revisions and amendments
- Integration with budget approval workflows
- Advanced variance analysis with trend indicators
- Mobile-responsive design improvements
- Integration with dashboard widgets
