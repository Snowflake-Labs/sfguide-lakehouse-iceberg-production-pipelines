First, ask me the following before you start building:

1. What database.schema has my game's Dynamic Tables?
2. Where should the Streamlit app and stage be created?
3. What warehouse should it use?

Then, build me a multi-page Streamlit in Snowflake dashboard for my balloon popper game using the Dynamic Tables from the schema above.

Structure the app in its own directory with a pages/ directory:

- streamlit_app.py — home page with a game summary and key metrics
- pages/1_Leaderboard.py — top 5 player rankings, score gaps, bar chart
- pages/2_Color_Breakdown.py — pops by color, avg points per pop, player-color heatmap, players favorite color
- pages/3_Trends.py — color value over time, player scores over time

I want to answer: 
  * Who is winning and by how much? 
  * Which colors are most popular? 
  * Which color is worth more points? How are scores trending?

Make it auto-refreshing, clean charts, easy to read at a glance. Handle missing data gracefully. Add a color scheme toggle. Use get_active_session(), wide layout, lowercase column names from Snowpark before passing to pandas. 
