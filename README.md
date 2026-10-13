<div align="center">

# Flexible Budget

**Revenue-Responsive & Multi-Dimensional Budget Control for ERPNext**

Keep spending aligned with approved budgets, business dimensions and revenue achievement.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](license.txt)
[![Frappe v15–v16](https://img.shields.io/badge/Frappe-v15%E2%80%93v16-orange.svg)](https://frappeframework.com/)
[![ERPNext Integration](https://img.shields.io/badge/ERPNext-Accounting%20%26%20Buying-green.svg)](https://erpnext.com/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

**📊 Multi-Dimensional Budgets &nbsp;&nbsp; 🎯 Revenue Targets &nbsp;&nbsp; 🛡️ Spending Controls**

**🏢 Branch & Department Analysis &nbsp;&nbsp; 📈 Variance Reporting &nbsp;&nbsp; 🔗 ERPNext Integration**

</div>

<p align="right"><sub>by <a href="https://www.aakvatech.com">Aakvatech</a></sub></p>

## About Flexible Budget

Flexible Budget is an open-source Frappe application that extends ERPNext with revenue-responsive, multi-dimensional expenditure controls. It lets finance teams budget for particular accounts and accounting dimensions, monitor revenue targets and determine how much of an approved budget is currently available based on revenue achievement.

For example, a business can approve an expense budget for a branch while limiting the immediately available amount in proportion to the branch's achieved revenue target. Transaction checks help bring those controls into daily procurement and accounting workflows.

The application **extends ERPNext; it is not a standalone accounting or budgeting engine**.

## Key Features

- **Multi-Dimensional Budgets:** Allocate amounts to income or expense accounts against selected accounting dimensions, including Branch and other configured dimensions.
- **Revenue-Responsive Limits:** Calculate the allowed amount from the budget and target achievement percentage, instead of relying only on a static ceiling.
- **Company-Level Policies:** Configure budget frequency (weekly, monthly, quarterly, half-yearly or yearly), target calculation method and budget-exceeding actions.
- **Target Revenue Tracking:** Record company- and branch-specific targets, earned revenue, achievement percentage and optional earned-amount overrides.
- **Transaction Controls:** Validate ERPNext Material Requests, Purchase Orders, Purchase Invoices, Journal Entries and Expense Claims against applicable budgets.
- **Configurable Responses:** Set **Stop**, **Warn** or **Ignore** actions for supported transaction stages.
- **Budget Variance Reporting:** Review monthly budget, allowed spend, actual expenditure, variance, utilization and target performance by accounting dimension.
- **Automated Revenue Refresh:** A scheduled job refreshes revenue information, supplemented by a background update on Target Revenue submission.

> **Important:** A budget's configured **Stop** behavior is enforced at submission; during earlier save events the implementation can show a warning instead. Validate the complete approval workflow on a test site before relying on it as an authorization control.

## Business Problems This App Solves

| Business challenge | Flexible Budget approach |
| --- | --- |
| Fixed annual budgets do not reflect changing business activity | Tie allowable expenditure to recorded revenue achievement |
| Spending control is too broad for multi-branch organizations | Target selected branches and accounting dimensions |
| Finance identifies overspending only after transactions are posted | Validate supported procurement and accounting transactions during processing |
| Budget and actual performance are difficult to compare | Analyze monthly variances and utilization |
| Different companies or transaction types need different policies | Set company defaults and per-budget Stop, Warn or Ignore actions |

## Who Should Use It?

**Suitable for:** Multi-branch businesses, finance controllers, budget owners, procurement teams, and organizations whose operating expenditure needs to respond to realized revenue.

**Not designed for:** Standalone use without ERPNext; organizations needing cash-flow forecasting or a full budget approval workflow out of the box; or deployments that cannot maintain accurate revenue targets and accounting dimensions.

## Business Benefits

- Better visibility of available expenditure versus original budget allocation.
- More granular accountability by branch, account, project or other applicable dimensions.
- Earlier notification of spending outside established limits.
- More consistent finance policies across purchasing and expense booking.
- Improved period-by-period analysis for management reviews.

Actual savings and control effectiveness depend on master-data quality, configuration and operational compliance; no particular ROI is guaranteed.

## Before and After

| Without Flexible Budget | With Flexible Budget |
| --- | --- |
| Spending ceilings typically remain static | Available limits can change with recorded revenue achievement |
| Budget checks are often manual or tied to fewer dimensions | Checks can use matched combinations of accounting dimensions |
| Managers reconcile budgets and actuals separately | A dedicated variance report consolidates the analysis |
| Procurement policies are applied inconsistently | Configurable Stop, Warn and Ignore responses support consistent application |

## Operational Flow

```text
Company Budget Control
  ├─ Budget frequency and transaction policies
  └─ Fixed or revenue-based target settings
                │
                ▼
Multi-Dimensional Budget
  ├─ Company, period and accounting dimensions
  ├─ Budget accounts and approved amounts
  └─ Transaction-specific control actions
                │
                ├───────────────┐
                ▼               ▼
         Target Revenue     ERPNext transactions
         ├─ Company/Branch  ├─ Material Request
         ├─ Target amount   ├─ Purchase Order
         └─ Earned amount   ├─ Purchase Invoice
                │           ├─ Journal Entry
                ▼           └─ Expense Claim
      Achievement %               │
                │                 │
                └────────┬────────┘
                         ▼
         Allowed budget = budget × achievement %
                         │
                         ▼
             Stop / Warn / Ignore
                         │
                         ▼
          Multi-Dimensional Budget Variance
```

**Illustrative example:** If an account has an approved budget of TZS 10,000,000 and its matching revenue achievement is 70%, its calculated allowed amount is TZS 7,000,000. The validator compares applicable commitments and expenditure with the allowed amount. Actual calculations also depend on document status, accounting dimensions and the revenue target period.

## ERPNext Integration

Flexible Budget works with ERPNext's **Company, Account, Accounting Dimension, Branch, Fiscal Year and General Ledger** data. It registers document-event validations for:

| ERPNext transaction | Hook events |
| --- | --- |
| Material Request | Before Save, On Submit |
| Purchase Order | Before Save, On Submit |
| Purchase Invoice | Before Save, On Submit |
| Journal Entry | Before Save, On Submit |
| Expense Claim | Before Save, On Submit |

The variance report reads submitted Multi-Dimensional Budgets and actual accounting activity. It is **not** an ERPNext standard Budget report and does not automatically combine ERPNext's standard Budget records with this app's budgets.

## Compatibility

| Component | Requirement |
| --- | --- |
| Frappe Framework | `>=15.0.0,<17.0.0` declared in `pyproject.toml` |
| ERPNext | Required in practice: controllers and reports reference ERPNext modules, accounting DocTypes and transactions |
| Python | 3.10+ |
| App identifier | `flexible_budget` |
| Documented source branch | `version-16-hotfix` |

This README documents the v16 hotfix branch. The declared Frappe version range is broader than a verified compatibility matrix; test on the exact Frappe/ERPNext versions used in production.

## Installation

**Prerequisites:** A working Frappe Bench site with a compatible ERPNext installation, configured companies, accounts, fiscal years and accounting dimensions.

```bash
bench get-app --branch version-16-hotfix https://github.com/Aakvatech-Limited/flexible-budget.git
bench --site your-site.local install-app flexible_budget
bench --site your-site.local migrate
```

Replace `your-site.local` with the actual site name. Test in staging and back up the database before installing on a production site.

## Initial Configuration

1. **Prepare ERPNext masters.** Ensure Company, Fiscal Year, Account, Branch and any required accounting dimensions are configured and users have appropriate roles.
2. **Create Company Budget Control.** Select the company, frequency, target calculation method (Fixed Target or Revenue-Based Target), and the applicable transaction policy settings.
3. **Create a Multi-Dimensional Budget.** Enter the company and start date, select accounting dimension/value pairs, and add budget accounts and amounts. The period end date is derived from the configured frequency.
4. **Include Branch.** The budget controller explicitly requires a Branch dimension before submission.
5. **Submit Target Revenue records.** Select company, branch and period; enter or calculate the target and earned amounts according to the company policy. Verify the percentage used for budget enforcement.
6. **Test transaction controls.** Create sample Material Requests, Purchase Orders and expense documents under and over the allowed limit. Confirm save warnings and submission outcomes.
7. **Run the Multi-Dimensional Budget Variance report.** Choose company and fiscal-year range; optionally filter by account, cost center, project, branch and department.

**Operational caution:** The validator currently returns without enforcing a limit when there is no matching submitted Multi-Dimensional Budget. Design the rollout policy accordingly; absence of a matching budget must not be assumed to mean a blocked transaction.

## Modules and DocTypes

| DocType | Purpose |
| --- | --- |
| Company Budget Control | Company-specific budget frequency, policies and revenue-target settings |
| Multi-Dimensional Budget | Submittable budget record, dimension combinations, accounts and control actions |
| Multi-Dimensional Budget Account | Child rows containing account and budget amount |
| Multi-Dimensional Budget Detail | Child rows defining accounting dimension and selected value |
| Target Revenue | Submittable company/branch revenue targets and achievement calculations |

## Reports and Analytics

### Multi-Dimensional Budget Variance

The included report provides month-by-month analysis of:

- Original budget amount
- Target revenue, earned revenue and achievement percentage
- Revenue-adjusted allowed amount
- Actual amount, variance amount and variance percentage
- Utilization percentage
- Dimension-level filtering and chart/summary output

**Required filters:** Company, From Fiscal Year and To Fiscal Year. Optional filters include date range, Account, Cost Center, Project, Branch and Department.

See [the report's technical README](flexible_budget/flexible_budget/report/multi_dimensional_budget_variance/README.md) for additional explanation. Verify optional report actions against the live implementation before treating them as supported workflows.

## Permissions and Security

The repository's DocType permissions explicitly include:

- **System Manager:** Company Budget Control and Target Revenue management.
- **Accounts Manager:** Multi-Dimensional Budget creation, submission and amendment.
- **Report access:** Governed by the report definition, role permissions and deployment configuration.

Review access to financial dimensions and transactions before production use. The app includes custom fields and a bypass-validation mechanism; restrict any bypass capability to authorized users and audit exceptions. Budget validation should be tested for API, import and workflow submissions, not only through the Desk form.

## Technical Architecture

- Standard Frappe DocTypes and Python document controllers implement configuration, validation and target calculations.
- `hooks.py` registers ERPNext document-event validators.
- `flexible_budget/flexible_budget/utils.py` contains budget checking and revenue utilities.
- `scheduler_events` schedules `update_revenue` daily at **00:30 server time**.
- Target Revenue submission enqueues a revenue refresh after database commit.
- Install/migrate hooks apply custom fields and property setters.
- The report combines a Python Script Report with JavaScript filters and formatting.

### Project Structure

```text
flexible_budget/
├── flexible_budget/
│   ├── flexible_budget/
│   │   ├── doctype/
│   │   │   ├── company_budget_control/
│   │   │   ├── multi_dimensional_budget/
│   │   │   ├── multi_dimensional_budget_account/
│   │   │   ├── multi_dimensional_budget_detail/
│   │   │   └── target_revenue/
│   │   ├── report/multi_dimensional_budget_variance/
│   │   └── utils.py
│   ├── patches/
│   ├── hooks.py
│   └── patches.txt
├── pyproject.toml
├── license.txt
└── README.md
```

## Developer Setup and Testing

After installing on a development Bench, run the relevant Frappe app test suite:

```bash
bench --site your-site.local run-tests --app flexible_budget
```

The repository includes controller, budget-validation, hook, variance-report and end-to-end test modules. It also includes Ruff/pre-commit and GitHub Actions configuration. Passing CI does not replace functional validation on your ERPNext deployment.

## Migration and Upgrades

Use the appropriate maintained branch for your target framework version and back up the site before upgrading. Installation and migration hooks apply custom-field and property-setter customizations. Review their impact alongside other apps that customize the same DocTypes.

```bash
bench --site your-site.local backup --with-files
bench --site your-site.local migrate
```

After upgrading, test the budget approval lifecycle, scheduled revenue refresh, transaction validations, custom fields and variance report.

## Uninstallation

Before uninstalling, back up site data and identify business records, customizations and dependencies that may be affected. Use the standard Bench uninstall procedure only after validating the impact in a test environment. No dedicated uninstall cleanup hook is configured in this branch.

## Risks and Considerations

- **Revenue accuracy:** Allowed budget depends on revenue-target matching and recorded achievement. Missing or stale targets can distort limits.
- **Budget matching:** No matching submitted budget currently results in no enforcement for that transaction.
- **Branch requirement:** A Branch dimension is mandatory on budget submission.
- **Enforcement stage:** Stop policies behave differently at save and submit; test both.
- **Transaction coverage:** Validation applies to the listed ERPNext DocTypes; other transaction paths should not be assumed covered.
- **Data and query safety:** Finance and engineering teams should review dynamic SQL construction in budget utilities before exposing the app to untrusted dimension inputs.
- **Customization conflicts:** Installation/migration can modify standard ERPNext DocTypes through custom fields and property setters.

## Frequently Asked Questions

**Does this replace standard ERPNext budgeting?**  
No. It provides its own Multi-Dimensional Budget documents, revenue-adjusted limits and corresponding report.

**Can budgets vary by branch?**  
Yes. Branch is a required dimension; additional configured dimensions can further identify a budget.

**Does budget availability automatically track revenue?**  
The app provides revenue update routines and an achievement-based calculation. Correct results depend on settings, matching Target Revenue records and scheduled-job health.

**Can a transaction exceed a budget?**  
Depending on the configured action and processing stage, the application can stop submission, warn or ignore. Test exception handling and permissions before going live.

**Is this a standalone Frappe app?**  
No. Although the package metadata declares a Frappe version range, its current functional code imports and uses ERPNext accounting functionality.

## Support and Contributions

For defects, enhancement requests and contributions, use the [Flexible Budget GitHub repository](https://github.com/Aakvatech-Limited/flexible-budget). Contributions should include tests for revenue calculations, budget matching, transaction hooks and report correctness.

## Credits and License

Developed and maintained by **[Aakvatech Limited](https://www.aakvatech.com)**, with contributors acknowledged in the source files.

Licensed under the **MIT License**; see [license.txt](license.txt). **Maintainer action:** The license file currently contains the placeholders `[year]` and `[fullname]`; replace them with the correct copyright attribution after confirming ownership.

## Repository Evidence Reviewed

The information above is based on `pyproject.toml`, `hooks.py`, the Company Budget Control / Multi-Dimensional Budget / Target Revenue controllers and DocType definitions, `utils.py`, the Multi-Dimensional Budget Variance report, migration hooks and tests on `version-16-hotfix`.

### To Confirm Before Publishing

- Exact supported ERPNext/Frappe v15 and v16 patch releases and real-site test results.
- Business ownership and final copyright attribution.
- Approved behavior when no matching budget or revenue target exists.
- Whether the validation-bypass custom fields require additional role restrictions.
- Whether optional variance-report export or budget-adjustment UI actions are actually available and production-ready.
- Real screenshots of the budget setup, target form and variance report.

