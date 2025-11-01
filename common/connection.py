from django.db import connections

def execute_raw_query(db_alias, query, params=None, fetch=False):
    """
    Hàm thực thi query SQL thuần trên database được chọn.

    Args:
        db_alias (str): Tên database trong settings.py (vd: 'domjudge' hoặc 'default')
        query (str): Câu SQL (có thể chứa %s)
        params (list | tuple): Tham số truyền vào query (optional)
        fetch (bool): Nếu True → trả về kết quả SELECT

    Returns:
        list[tuple] | None: danh sách kết quả nếu fetch=True, ngược lại None
    """
    with connections[db_alias].cursor() as cursor:
        cursor.execute(query, params or [])
        if fetch:
            columns = [col[0] for col in cursor.description] if cursor.description else []
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results