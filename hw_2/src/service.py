from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from openapi_server.models.product_create import ProductCreate
from openapi_server.models.product_update import ProductUpdate
from openapi_server.models.product_response import ProductResponse
from openapi_server.models.product_page_response import ProductPageResponse


@dataclass
class ProductService:
    db: Session

    def create(self, dto: ProductCreate) -> ProductResponse:
        new_id = str(uuid4())
        price = Decimal(dto.price)  

        row = self.db.execute(
            text(
                """
                insert into products (id, name, description, price, stock, category, status)
                values (:id, :name, :description, :price, :stock, :category, :status)
                returning id, name, description, price, stock, category, status, created_at, updated_at
                """
            ),
            {
                "id": new_id,
                "name": dto.name,
                "description": dto.description,
                "price": price,
                "stock": dto.stock,
                "category": dto.category,
                "status": dto.status,
            },
        ).mappings().one()

        self.db.commit()
        return self._to_product_response(row)

    def get(self, product_id: str) -> Optional[ProductResponse]:
        row = self.db.execute(
            text(
                """
                select id, name, description, price, stock, category, status, created_at, updated_at
                from products
                where id = :id
                """
            ),
            {"id": product_id},
        ).mappings().first()

        if row is None:
            return None

        return self._to_product_response(row)

    def list(
        self,
        page: int = 0,
        size: int = 20,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> ProductPageResponse:
        where_sql, params = self._build_filters(status=status, category=category)

        total = self.db.execute(
            text(f"select count(*) as cnt from products {where_sql}"),
            params,
        ).mappings().one()["cnt"]

        rows = self.db.execute(
            text(
                f"""
                select id, name, description, price, stock, category, status, created_at, updated_at
                from products
                {where_sql}
                order by created_at desc
                offset :offset
                limit :limit
                """
            ),
            {**params, "offset": page * size, "limit": size},
        ).mappings().all()

        items = [self._to_product_response(r) for r in rows]

        
        return ProductPageResponse.from_dict(
            {
                "items": [i.to_dict() for i in items],
                "totalElements": int(total),
                "page": page,
                "size": size,
            }
        )

    def update(self, product_id: str, dto: ProductUpdate) -> Optional[ProductResponse]:
        price = Decimal(dto.price)

        row = self.db.execute(
            text(
                """
                update products
                set name = :name,
                    description = :description,
                    price = :price,
                    stock = :stock,
                    category = :category,
                    status = :status
                where id = :id
                returning id, name, description, price, stock, category, status, created_at, updated_at
                """
            ),
            {
                "id": product_id,
                "name": dto.name,
                "description": dto.description,
                "price": price,
                "stock": dto.stock,
                "category": dto.category,
                "status": dto.status,
            },
        ).mappings().first()

        if row is None:
            self.db.rollback()
            return None

        self.db.commit()
        return self._to_product_response(row)

    def archive(self, product_id: str) -> bool:
        row = self.db.execute(
            text(
                """
                update products
                set status = 'ARCHIVED'
                where id = :id
                returning id
                """
            ),
            {"id": product_id},
        ).mappings().first()

        # if row is None:
        #     self.db.rollback()
        #     return False

        self.db.commit()
        return True


    def _build_filters(self, status: Optional[str], category: Optional[str]):
        clauses = []
        params = {}

        if status is not None:
            clauses.append("status = :status")
            params["status"] = status

        if category is not None:
            clauses.append("category = :category")
            params["category"] = category

        if clauses:
            return "where " + " and ".join(clauses), params
        return "", params

    def _to_product_response(self, row) -> ProductResponse:
        return ProductResponse.from_dict(
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "price": str(row["price"]),
                "stock": int(row["stock"]),
                "category": row["category"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
        )

