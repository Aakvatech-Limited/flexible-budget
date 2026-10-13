# Flexible Budget navigation for Frappe v16.50+

This branch adds standard app-owned Dock, Sidebar, Workspace, Dashboard, Dashboard Charts and Number Cards. The data displayed on this dashboard is **record counts**, not currency amounts or financial variance. Use **Multi-Dimensional Budget Variance** for monetary and revenue-sensitive measures.

## Navigation

Dock: **Flexible Budget** → Sidebar: **Flexible Budget** → Workspace: **Flexible Budget**.

| Navigation area | Type | Source |
| --- | --- | --- |
| Multi-Dimensional Budget | DocType | App-owned, Accounts Manager |
| Target Revenue | DocType | App-owned, System Manager |
| Budget Variance | Report | App-owned Multi-Dimensional Budget Variance |
| Budget Control Dashboard | Dashboard | App-owned Flexible Budget Control |
| Company Budget Control | DocType | App-owned, System Manager |

Child table DocTypes are deliberately excluded from direct navigation. The dashboard groups submitted budgets by company and submitted revenue targets by branch. Cards count submitted budget and target records and configured companies; they are not a measure of budget value or available spend.

## Installation and validation

1. Install/update on a staging Frappe **v16.50+** site with ERPNext and run `bench --site SITE migrate`.
2. Confirm standard Dock, Sidebar, Workspace, Dashboard, Dashboard Chart and Number Card records were synchronized from app JSON.
3. As System Manager, open the Apps screen and Flexible Budget dock entry; verify all routes, dashboard charts and card counts.
4. Verify Accounts Manager and an ordinary restricted role; navigation must not grant new DocType or report access.
5. On a previously customized site, verify the app Dock item is enabled in the user's arrangement. Existing dock customizations can hide new entries.
6. Check dashboard calculation against actual submitted records; verify null/empty grouping behavior and chart display on the deployed Frappe patch level.

These files follow existing Aakvatech v16 native-export patterns but were assembled from repository source **without a live v16.50 site export or runtime execution**. Verify the final record format and permissions in a real site before merging.
