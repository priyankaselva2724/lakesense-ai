import os
os.environ.setdefault("LAKE_FORMAT", "parquet")  # tests use plain Parquet; Docker uses Delta Lake
import subprocess
try:  # Spark 3.5 on Java 21 needs extra --add-opens flags; harmless elsewhere
    out = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr
    if 'version "21' in out or 'version "22' in out or 'version "23' in out:
        os.environ["SPARK_JAVA_OPENS"] = "1"
except Exception:
    pass
