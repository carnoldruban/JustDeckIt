# Quality Control Notes

## Prompt Goal
The goal of this prompt is to assess an AI model's ability to perform a complex, multi-step data analysis task involving three separate datasets. The model must integrate data, perform geospatial and socio-economic analysis, calculate derived metrics, generate multiple advanced visualizations, and synthesize its findings into a strategic business recommendation.

## Step-by-Step Solution

### Part 1: Operator Market Share & Geospatial Footprint

1.  **Load Data:** Load `charging_sessions.csv` and `charging_stations.csv`.
2.  **Join Datasets:** Perform a left join between `charging_sessions` and `charging_stations` on `station_id`.
3.  **Calculate Market Share:** Group the joined data by `operator_name` and calculate the sum of `kwh_charged` for each operator. This will determine the market share based on energy delivered.
4.  **Prepare Geospatial Data:** From the `charging_stations` dataset, use `longitude`, `latitude`, `operator_name`, and `plugs_count` for plotting.
5.  **Generate Geospatial Scatter Plot:**
    *   Create a scatter plot using `longitude` for the x-axis and `latitude` for the y-axis.
    *   Map the `operator_name` to the color of each point.
    *   Map the `plugs_count` to the size of each point.
    *   The plot should have a title (e.g., "Geospatial Distribution of EV Charging Stations in Warsaw"), axis labels, and a legend explaining the color-to-operator mapping.

### Part 2: Socio-Economic Charging Behavior Analysis

1.  **Load Data:** Load `charging_sessions.csv` and `customers.csv`.
2.  **Join Datasets:** Perform a left join between `charging_sessions` and `customers` on `customer_id`.
3.  **Group by Income Tier:** Group the joined data by the customer's `income_tier` ('Low-Mid', 'Mid-Range', 'High').
4.  **Calculate Averages:** For each income tier, calculate the average `total_cost` and the average `kwh_charged`.
5.  **Present in Table:** Display the results in a clear summary table with columns: `Income Tier`, `Average Total Cost`, `Average kWh Charged`.

### Part 3: Battery Efficiency vs. Charging Cost

1.  **Use Joined Data:** Use the joined data from Part 2 (`charging_sessions` and `customers`). This data should already contain `kwh_charged` and `battery_capacity_kwh`.
2.  **Calculate Derived Metric:** Create a new column, `charge_to_capacity_ratio`, by dividing `kwh_charged` by `battery_capacity_kwh`. Handle any potential division by zero or missing capacity values.
3.  **Analyze Correlation:** Examine the relationship between `charge_to_capacity_ratio` and `cost_per_kwh`.
4.  **Generate Scatter Plot:**
    *   Create a scatter plot with `charge_to_capacity_ratio` on the x-axis and `cost_per_kwh` on the y-axis.
    *   Add a regression line to visualize the trend.
    *   The plot should have a title (e.g., "Charging Cost per kWh vs. Battery Charge Ratio"), and clear axis labels.

### Part 4: Strategic Recommendation for High-Income Districts

1.  **Load Data:** Load `charging_sessions.csv` and `charging_stations.csv`.
2.  **Join Datasets:** Join the two datasets on `station_id`.
3.  **Filter for High-Income Districts:** Filter the joined data to include only stations where the `income_tier` (from `charging_stations`) is 'High'.
4.  **Identify Dominant Operator:** Group the filtered data by `operator_name` and calculate the sum of `kwh_charged`. The operator with the highest total kWh is the most dominant in high-income districts.
5.  **Formulate Recommendation:** Based on the identity of the dominant operator, provide a strategic recommendation. For example: "The dominant operator in high-income districts is [Operator Name]. Given their strong market presence, a partnership strategy would be more effective than direct competition, allowing us to leverage their existing customer base."

## Code Used to Obtain Answers

```python
import pandas as pd
import plotly.express as px
import numpy as np

# Load the datasets
customers_df = pd.read_csv('customers.csv')
stations_df = pd.read_csv('charging_stations.csv')
sessions_df = pd.read_csv('charging_sessions.csv')


# --- Part 1: Operator Market Share & Geospatial Footprint ---
# Join sessions with stations to link operator data to charging data
sessions_with_stations_df = pd.merge(sessions_df, stations_df, on='station_id', how='left')

# Calculate market share by total kWh charged per operator
market_share_kwh = sessions_with_stations_df.groupby('operator_name')['kwh_charged'].sum().reset_index()
market_share_kwh = market_share_kwh.sort_values('kwh_charged', ascending=False)
print("Market Share by Total kWh Charged:")
print(market_share_kwh)

# Generate geospatial scatter plot
fig1 = px.scatter_mapbox(
    stations_df,
    lat="latitude",
    lon="longitude",
    color="operator_name",
    size="plugs_count",
    hover_name="district_name",
    hover_data={"operator_name": True, "plugs_count": True},
    title="Geospatial Distribution of EV Charging Stations in Warsaw",
    mapbox_style="carto-positron",
    zoom=10,
    size_max=15
)
# fig1.show()


# --- Part 2: Socio-Economic Charging Behavior Analysis ---
# Join sessions with customers
sessions_with_customers_df = pd.merge(sessions_df, customers_df, on='customer_id', how='left')

# Group by customer income tier and calculate average cost and kWh
socio_economic_analysis = sessions_with_customers_df.groupby('income_tier').agg(
    average_total_cost=('total_cost', 'mean'),
    average_kwh_charged=('kwh_charged', 'mean')
).reset_index()

print("Socio-Economic Charging Behavior:")
print(socio_economic_analysis)


# --- Part 3: Battery Efficiency vs. Charging Cost ---
# Use the dataframe from Part 2 which already includes battery capacity
analysis_df_part3 = sessions_with_customers_df.dropna(subset=['battery_capacity_kwh'])
analysis_df_part3 = analysis_df_part3[analysis_df_part3['battery_capacity_kwh'] > 0]

# Calculate the charge-to-capacity ratio
analysis_df_part3['charge_to_capacity_ratio'] = analysis_df_part3['kwh_charged'] / analysis_df_part3['battery_capacity_kwh']

# Generate scatter plot with regression line
fig2 = px.scatter(
    analysis_df_part3,
    x='charge_to_capacity_ratio',
    y='cost_per_kwh',
    title='Charging Cost per kWh vs. Battery Charge Ratio',
    trendline='ols', # Ordinary Least Squares regression line
    labels={
        'charge_to_capacity_ratio': 'Charge-to-Capacity Ratio (kWh Charged / Battery Capacity)',
        'cost_per_kwh': 'Cost per kWh'
    }
)
# fig2.show()


# --- Part 4: Strategic Recommendation for High-Income Districts ---
# Use the dataframe from Part 1
high_income_sessions = sessions_with_stations_df[sessions_with_stations_df['income_tier'] == 'High']

# Identify dominant operator in these districts by total kWh charged
dominant_operator_high_income = high_income_sessions.groupby('operator_name')['kwh_charged'].sum().reset_index()
dominant_operator_high_income = dominant_operator_high_income.sort_values('kwh_charged', ascending=False)

if not dominant_operator_high_income.empty:
    top_operator = dominant_operator_high_income.iloc[0]['operator_name']
    print("Dominant Operator in High-Income Districts:")
    print(dominant_operator_high_income)

    print("\n--- Strategic Recommendation ---")
    print(f"The most dominant operator in districts classified as 'High' income_tier is '{top_operator}'.")
    print("Recommendation: Given their established dominance and strong footprint in these valuable areas, a strategic partnership is recommended. Competing directly would require significant capital investment to overcome their market share and brand recognition. A partnership would allow us to tap into their existing infrastructure and customer base, accelerating our entry into this lucrative market segment.")
else:
    print("No charging sessions found in districts classified as 'High' income_tier.")

```