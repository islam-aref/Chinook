import sqlite3
def line() :
    print('-'*40)

conn = sqlite3.connect('Chinook_Sqlite.sqlite')

cursor = conn.cursor()

years=cursor.execute("""
    SELECT 
        MIN(InvoiceDate) as FirstInvoice,
        MAX(InvoiceDate) as LastInvoice
    FROM Invoice;
""").fetchall()

print(years)
line()

kpi_query = """
    SELECT
        SUM(Total) AS TotalRevenue,
        COUNT(DISTINCT InvoiceId) AS TotalInvoices,
        SUM(Total) / COUNT(DISTINCT InvoiceId) AS AvgInvoiceValue,
        (SELECT SUM(Quantity) FROM InvoiceLine) AS TotalTracksSold
    FROM Invoice;
""" 
kpis = cursor.execute(kpi_query).fetchone()
print(f"Total Revenue: ${kpis[0]:,.2f}")
print(f"Total Invoices: {kpis[1]}")
print(f"Average Invoice Value: ${kpis[2]:,.2f}")
print(f"Total Tracks Sold: {kpis[3]}")

line()

top_tracks_revenue_query = """
    SELECT 
        t.Name AS TrackName,
        ar.Name AS ArtistName,
        SUM(il.Quantity) AS TotalQuantitySold, -- Added this column
        SUM(il.UnitPrice * il.Quantity) AS TotalRevenue
    FROM InvoiceLine il
    JOIN Track t ON il.TrackId = t.TrackId
    JOIN Album al ON t.AlbumId = al.AlbumId
    JOIN Artist ar ON al.ArtistId = ar.ArtistId
    GROUP BY il.TrackId
    ORDER BY TotalRevenue DESC
    LIMIT 10;
"""
top_revenue = cursor.execute(top_tracks_revenue_query).fetchall()
print("\nTop 10 Tracks by Revenue:")
for track in top_revenue:
    print(f"{track[0]} by {track[1]} - ${track[3]:,.2f} (from {track[2]} units sold)")

line()

# Best Year by Sales
best_year_query = """
    SELECT 
        STRFTIME('%Y', InvoiceDate) AS Year,
        SUM(Total) AS YearlyRevenue,
        COUNT(*) AS InvoicesCount
    FROM Invoice
    GROUP BY Year
    ORDER BY YearlyRevenue DESC
    LIMIT 1;
""" 
best_year = cursor.execute(best_year_query).fetchone()
print(f"\nBest Year: {best_year[0]} with ${best_year[1]:,.2f} in revenue ({best_year[2]} invoices)")

line()

# Monthly Trend and Month-over-Month Growth for the last 3 years
mom_growth_query = """
WITH MonthlySales AS (
    SELECT 
        STRFTIME('%Y-%m', InvoiceDate) AS YearMonth,
        SUM(Total) AS MonthlyRevenue
    FROM Invoice
    WHERE InvoiceDate >= (SELECT DATE(MAX(InvoiceDate), '-3 years') FROM Invoice) -- Filter last 3 years
    GROUP BY YearMonth
)
SELECT
    YearMonth,
    MonthlyRevenue,
    LAG(MonthlyRevenue, 1) OVER (ORDER BY YearMonth) AS PreviousMonthRevenue,
    ROUND( 
        ((MonthlyRevenue - LAG(MonthlyRevenue, 1) OVER (ORDER BY YearMonth)) / LAG(MonthlyRevenue, 1) OVER (ORDER BY YearMonth)) * 100, 
        1
    ) AS MoMGrowthPercent
FROM MonthlySales
ORDER BY YearMonth;
"""
mom_data = cursor.execute(mom_growth_query).fetchall()
print("\nMonthly Revenue with MoM Growth (%):")
for month in mom_data:
    growth_text = f"{month[3]}%" if month[3] is not None else "N/A (First Month)"
    print(f"{month[0]}: ${month[1]:,.2f} | Growth: {growth_text}")

line()

# Revenue by Country (Top 5 + Others)
region_query = """
WITH CountryRevenue AS (
    SELECT
        c.Country,
        SUM(i.Total) AS TotalRevenue,
        COUNT(*) AS InvoiceCount
    FROM Invoice i
    JOIN Customer c ON i.CustomerId = c.CustomerId
    GROUP BY c.Country
),
CountryRank AS (
    SELECT *,
    RANK() OVER (ORDER BY TotalRevenue DESC) as RevenueRank
    FROM CountryRevenue
)
SELECT
    CASE WHEN RevenueRank <= 5 THEN Country ELSE 'Other Countries' END AS Bucket,
    SUM(TotalRevenue) AS TotalRevenue,
    SUM(InvoiceCount) AS TotalInvoices,
    CASE WHEN RevenueRank <= 5 THEN Country ELSE NULL END AS OriginalCountry -- Keep detail for top 5
FROM CountryRank
GROUP BY Bucket
ORDER BY TotalRevenue DESC;
"""
region_data = cursor.execute(region_query).fetchall()
print("\nRevenue by Region:")
for region in region_data:
    print(f"{region[0]}: ${region[1]:,.2f} ({region[2]} invoices)")

line()
line()



conn.commit()