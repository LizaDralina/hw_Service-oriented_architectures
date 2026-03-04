from sqlalchemy import text
from sqlalchemy.orm import Session

def archive_product(db: Session, product_id: str) -> bool:
    res = db.execute(
        text("update products set status = 'ARCHIVED' where id = :id"),
        {"id": product_id},
    )
    
    return (res.rowcount or 0) > 0
