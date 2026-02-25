import pandas as pd
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
now = datetime.now(IST)

print(f"Now: {now}")

# Simulate Yesterday's boundaries
yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
yesterday_start = yesterday_end - timedelta(days=1)

print(f"Yesterday Start: {yesterday_start}")
print(f"Yesterday End: {yesterday_end}")

# Simulate a deal won TODAY
today_won_time = now.replace(hour=14, minute=0)
print(f"Today Won Time: {today_won_time}")

# Comparison test
is_in_yesterday = (today_won_time >= yesterday_start) and (today_won_time < yesterday_end)
print(f"Is Today's deal in Yesterday's window? {is_in_yesterday}")

# Dataframe test
df = pd.DataFrame({"closed_time": [today_won_time, yesterday_start + timedelta(hours=10)]})
df["closed_time"] = pd.to_datetime(df["closed_time"], utc=True).dt.tz_convert(IST)

print("\nDataframe:")
print(df)

filtered = df[(df["closed_time"] >= yesterday_start) & (df["closed_time"] < yesterday_end)]
print("\nFiltered (should only have 1 row):")
print(filtered)
