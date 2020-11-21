WITH removing AS (
    SELECT 
        phonenumber, 
        baseline_percentage, 
        duration, 
        original_price,
        current_price, 
        link,
        ROW_NUMBER() OVER (
            PARTITION BY 
                phonenumber,  
                link
            ORDER BY 
                phonenumber, 
                link
        ) row_num
     FROM 
        dbo.ScrapedData
)
DELETE FROM removing
WHERE row_num > 1;