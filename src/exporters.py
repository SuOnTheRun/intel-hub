import pandas as pd
from io import StringIO

def export_dataframe_csv(df: pd.DataFrame) -> bytes:
    buf = StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()
