# Evaluation Rubric

## Part 1: Operator Market Share & Geospatial Footprint
| Weight | Category | Criterion |
|---|---|---|
| 10 | Must-Have | Calculates the correct total `kwh_charged` for each operator (e.g., GreenWay: [Actual Value], Ekoenergetyka: [Actual Value], etc.). |
| 20 | Must-Have | Provides a geospatial scatter plot that is semantically equivalent to the reference plot, mapping station locations. |
| 10 | Must-Have | Displays the plot with longitude on the x-axis and latitude on the y-axis. |
| 8 | Must-Have | Colors the plot points based on the `operator_name`. |
| 8 | Must-Have | Sizes the plot points based on the `plugs_count`. |
| 5 | Good-to-Have | Includes a clear and accurate legend that maps colors to each `operator_name`. |

## Part 2: Socio-Economic Charging Behavior Analysis
| Weight | Category | Criterion |
|---|---|---|
| 15 | Must-Have | Presents the analysis in a summary table. |
| 10 | Must-Have | Calculates the correct average `total_cost` for each customer `income_tier` (e.g., High: [Actual Value], Mid-Range: [Actual Value], Low-Mid: [Actual Value]). |
| 10 | Must-Have | Calculates the correct average `kwh_charged` for each customer `income_tier` (e.g., High: [Actual Value], Mid-Range: [Actual Value], Low-Mid: [Actual Value]). |
| 5 | Good-to-Have | States that customers in the 'High' income tier tend to have both a higher average cost and higher energy consumption per session. |
| -25 | Must-Have | **[Failure Criterion]** Bases the socio-economic analysis on the charging station's district `income_tier` instead of the customer's `income_tier`. |

## Part 3: Battery Efficiency vs. Charging Cost
| Weight | Category | Criterion |
|---|---|---|
| 10 | Must-Have | Correctly calculates the `charge_to_capacity_ratio` by dividing `kwh_charged` by `battery_capacity_kwh`. |
| 15 | Must-Have | Provides a scatter plot visualizing the relationship between the `charge_to_capacity_ratio` and `cost_per_kwh`. |
| 10 | Must-Have | Includes a regression line on the scatter plot to show the trend. |
| 7 | Good-to-Have | Correctly interprets the trend from the regression line. |
| -30 | Must-Have | **[Failure Criterion]** Completely omits the "Battery Efficiency vs. Charging Cost" analysis and visualization. |

## Part 4: Strategic Recommendation for High-Income Districts
| Weight | Category | Criterion |
|---|---|---|
| 15 | Must-Have | Correctly filters the data to analyze only charging sessions in districts classified as 'High' `income_tier`. |
| 10 | Must-Have | Identifies the correct dominant operator in high-income districts based on total `kwh_charged`. |
| 10 | Must-Have | Provides a clear, data-driven recommendation on whether to partner with or compete against the dominant operator. |
| -20 | Must-Have | **[Failure Criterion]** Provides a generic or non-data-driven recommendation that does not directly address the strategic question asked in the prompt. |
