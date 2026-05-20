import re
from typing import Any, Dict, List

from text_to_sql_pipeline.schema import load_schema

TABLE_KEYWORDS = {
    "orders": ["order", "orders"],
    "customers": ["customer", "customers"],
    "payments": ["payment", "payments"],
    "employees": ["employee", "employees", "staff"],
    "offices": ["office", "offices"],
    "products": ["product", "products"],
    "productlines": ["product line", "product lines", "productline", "productlines"],
    "orderdetails": ["order detail", "order details", "orderdetail", "orderdetails"],
}

JOIN_MAP = {
    frozenset(("orders", "customers")): "orders.customerNumber = customers.customerNumber",
    frozenset(("payments", "customers")): "payments.customerNumber = customers.customerNumber",
    frozenset(("employees", "offices")): "employees.officeCode = offices.officeCode",
    frozenset(("orderdetails", "products")): "orderdetails.productCode = products.productCode",
    frozenset(("products", "productlines")): "products.productLine = productlines.productLine",
    frozenset(("customers", "employees")): "customers.salesRepEmployeeNumber = employees.employeeNumber",
    frozenset(("orders", "orderdetails")): "orders.orderNumber = orderdetails.orderNumber",
}

STATUS_VALUES = {
    "shipped": "Shipped",
    "resolved": "Resolved",
    "cancelled": "Cancelled",
    "on hold": "On Hold",
    "disputed": "Disputed",
    "in process": "In Process",
}


def decompose_question(question: str) -> Dict[str, Any]:
    text = " ".join((question or "").strip().split())
    lowered = text.lower()

    tables = detect_tables(lowered)
    if not tables:
        tables = ["orders"] if "order" in lowered else ["customers"]

    intent = detect_intent(lowered)
    columns = detect_columns(lowered, intent, tables)
    filters = detect_filters(text, lowered, tables)
    joins = detect_joins(tables)

    return {
        "intent": intent,
        "tables": tables,
        "columns": columns,
        "filters": filters or None,
        "joins": joins or None,
    }


def detect_tables(lowered: str) -> List[str]:
    detected: List[str] = []
    for table_name, keywords in TABLE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            detected.append(table_name)
    if "customer" in lowered and "order" in lowered and "customers" not in detected:
        detected.append("customers")
    if "customer" in lowered and "payment" in lowered and "customers" not in detected:
        detected.append("customers")
    return detected


def detect_intent(lowered: str) -> str:
    if any(token in lowered for token in ["how many", "count", "number of", "total number"]):
        return "AGGREGATE_COUNT"
    if any(token in lowered for token in ["total ", "sum "]):
        return "AGGREGATE_SUM"
    if any(token in lowered for token in ["average", "avg", "mean"]):
        return "AGGREGATE_AVG"
    if any(token in lowered for token in ["maximum", "max", "highest"]):
        return "AGGREGATE_MAX"
    if any(token in lowered for token in ["minimum", "min", "lowest"]):
        return "AGGREGATE_MIN"
    return "SELECT"


def detect_columns(lowered: str, intent: str, tables: List[str]) -> List[str]:
    if intent == "AGGREGATE_COUNT":
        return [f"COUNT({pick_count_column(tables)})"]
    if intent == "AGGREGATE_SUM":
        return [f"SUM({pick_metric_column(lowered, tables)})"]
    if intent == "AGGREGATE_AVG":
        return [f"AVG({pick_metric_column(lowered, tables)})"]
    if intent == "AGGREGATE_MAX":
        return [f"MAX({pick_metric_column(lowered, tables)})"]
    if intent == "AGGREGATE_MIN":
        return [f"MIN({pick_metric_column(lowered, tables)})"]

    selected_columns: List[str] = []
    schema = load_schema()
    keyword_map = {
        "name": ["customerName", "productName", "firstName", "lastName"],
        "city": ["city"],
        "country": ["country"],
        "price": ["buyPrice", "MSRP", "priceEach"],
        "amount": ["amount"],
        "date": ["orderDate", "paymentDate", "requiredDate", "shippedDate"],
        "status": ["status"],
        "phone": ["phone"],
        "vendor": ["productVendor"],
    }

    for keyword, candidate_columns in keyword_map.items():
        if keyword in lowered:
            for table_name in tables:
                actual_columns = schema.get(table_name, {}).get("columns", {})
                for candidate in candidate_columns:
                    if candidate.lower() in actual_columns and candidate not in selected_columns:
                        selected_columns.append(candidate)

    if not selected_columns:
        return ["*"]
    return selected_columns


def detect_filters(text: str, lowered: str, tables: List[str]) -> List[str]:
    filters: List[str] = []

    for status_keyword, actual_value in STATUS_VALUES.items():
        if status_keyword in lowered and "orders" in tables:
            filters.append(f"status = '{actual_value}'")

    country_patterns = [
        r"\bfrom\s+([A-Z][a-zA-Z]+)\s+customers\b",
        r"\bin\s+([A-Z][a-zA-Z]+)\b",
        r"\bfrom\s+([A-Z][a-zA-Z]+)\b",
    ]
    for pattern in country_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        country = match.group(1)
        if "customers" in tables or "offices" in tables:
            target_column = "country" if "customers" in tables else "country"
            filters.append(f"{target_column} = '{country}'")
            break

    date_match = re.search(r"\b(?:in|from)\s+(\d{4})\b", text)
    if date_match and "orders" in tables:
        year = date_match.group(1)
        filters.append(f"orderDate >= '{year}-01-01'")
        filters.append(f"orderDate < '{int(year) + 1}-01-01'")

    return dedupe(filters)


def detect_joins(tables: List[str]) -> List[str]:
    joins: List[str] = []
    for index, left_table in enumerate(tables):
        for right_table in tables[index + 1 :]:
            join = JOIN_MAP.get(frozenset((left_table, right_table)))
            if join:
                joins.append(join)
    return dedupe(joins)


def pick_count_column(tables: List[str]) -> str:
    preferred = {
        "orders": "orderNumber",
        "customers": "customerNumber",
        "payments": "customerNumber",
        "employees": "employeeNumber",
        "products": "productCode",
        "offices": "officeCode",
        "orderdetails": "orderNumber",
        "productlines": "productLine",
    }
    for table_name in tables:
        if table_name in preferred:
            return preferred[table_name]
    return "*"


def pick_metric_column(lowered: str, tables: List[str]) -> str:
    if "payment" in lowered or "revenue" in lowered or "amount" in lowered:
        return "amount"
    if "stock" in lowered or "quantity" in lowered:
        return "quantityInStock"
    if "msrp" in lowered:
        return "MSRP"
    if "price" in lowered:
        return "buyPrice"

    default_metric = {
        "payments": "amount",
        "products": "buyPrice",
        "orderdetails": "priceEach",
    }
    for table_name in tables:
        if table_name in default_metric:
            return default_metric[table_name]
    return pick_count_column(tables)


def dedupe(items: List[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for item in items:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output
