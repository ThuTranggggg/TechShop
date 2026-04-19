// Inspect the full behavioral graph
MATCH (u:User)-[r:VIEWED|CLICKED|ADDED_TO_CART]->(p:Product)
RETURN u.user_id AS user_id, type(r) AS action, p.product_id AS product_id, count(*) AS interactions
ORDER BY interactions DESC
LIMIT 50;

// Brand and category structure for a specific user
MATCH (u:User {user_id: $user_id})-[r:VIEWED|CLICKED|ADDED_TO_CART]->(p:Product)
OPTIONAL MATCH (p)-[:IN_BRAND]->(b:Brand)
OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
RETURN b.name AS brand, c.name AS category, count(r) AS interactions
ORDER BY interactions DESC;

// Related products for one item
MATCH (p:Product {product_id: $product_id})<-[:VIEWED|CLICKED|ADDED_TO_CART]-(u:User)-[r:VIEWED|CLICKED|ADDED_TO_CART]->(related:Product)
WHERE related.product_id <> $product_id
RETURN related.product_id AS product_id, count(r) AS score
ORDER BY score DESC
LIMIT 10;