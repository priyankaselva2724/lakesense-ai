import json, os, shutil, subprocess, sys
import duckdb, pytest
from lakesense import pipeline, simulate

pytest.importorskip("dbt")


def _dbt(args, env, cwd):
    r = subprocess.run([sys.executable, "-m", "dbt.cli.main"] + args + ["--profiles-dir", ".", "--project-dir", "."],
                       cwd=cwd, env=env, capture_output=True, text=True)
    return r


def test_dbt_gold_models_build_and_tests_pass(tmp_path):
    root = tmp_path / "proj"
    pipeline.run(root, n_orders=4000)
    simulate.generate_events(root / "data" / "raw", days=7)
    con = duckdb.connect(str(root / "data" / "warehouse.duckdb"))
    con.execute("drop table if exists silver.events")
    con.execute(f"""create table silver.events as select event_id, order_id, customer_id, category, event_type,
        cast(event_ts as timestamp) as event_ts, amount from read_json_auto('{(root / 'data/raw/events/events.jsonl').as_posix()}')
        where event_id is not null""")
    con.execute("drop schema gold cascade"); con.close()
    wd = tmp_path / "dbt"; shutil.copytree("dbt", wd)
    env = dict(os.environ, DBT_TARGET="duckdb", DUCKDB_PATH=str(root / "data" / "warehouse.duckdb"))
    for step in (["build"], ["build"]):  # second run exercises the incremental path
        r = _dbt(step, env, wd)
        assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]
    con = duckdb.connect(str(root / "data" / "warehouse.duckdb"), read_only=True)
    assert con.execute("select count(*) from gold.fact_orders").fetchone()[0] == con.execute("select count(*) from silver.orders").fetchone()[0]
