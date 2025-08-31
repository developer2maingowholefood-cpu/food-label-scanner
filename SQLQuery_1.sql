
SELECT *
FROM [dbo].[scan_comments] AS sc
JOIN scans AS s
ON s.id = sc.scan_id
ORDER BY s.timestamp DESC

SELECT *
FROM users

