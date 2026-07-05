"""
main.py — RPPI Maroc master pipeline runner

Usage:
  python main.py                  # full pipeline
  python main.py --ingest         # Phase 3: scrape data  { ingest for both mubawab(1) , agenz(2) OR ,ingest  source -- 1/2}
  python main.py --clean          # Phase 5: clean data
  python main.py --eda            # Phase 6: exploratory analysis
  python main.py --hedonic        # Phase 7-8-9: hedonic model + RPPI
  python main.py --index          # Phase 9: compute price index
  python main.py --dashboard      # Phase 14: launch Streamlit dashboard
  python main.py --schedule       # run daily at 06:00
"""

import sys, os, argparse, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))

from database.models import init_db
from utils.logger import log


def run_full_pipeline():
    from ingestion.pipeline      import run_ingestion
    from processing.cleaner      import run_cleaning
    from analytics.eda.exploratory import run_eda
    from analytics.index.rppi    import run_index

    log.info("╔══════════════════════════════════════════╗")
    log.info("║   RPPI Maroc — Full Pipeline             ║")
    log.info("╚══════════════════════════════════════════╝")

    init_db()
    run_ingestion()
    run_cleaning()
    run_eda()
    run_index()
    log.success("✅ Full pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RPPI Maroc Pipeline")
    parser.add_argument("--ingest",    action="store_true", help="Phase 3: scrape")
    parser.add_argument("--source",    default=None, help="limit --ingest to one source, e.g. agenz or mubawab")
    parser.add_argument("--clean",     action="store_true", help="Phase 5: clean")
    parser.add_argument("--eda",       action="store_true", help="Phase 6: EDA")
    parser.add_argument("--hedonic",   action="store_true", help="Phase 7-9: hedonic model")
    parser.add_argument("--index",     action="store_true", help="Phase 9: price index")
    parser.add_argument("--dashboard", action="store_true", help="Phase 14: dashboard")
    parser.add_argument("--schedule",  action="store_true", help="daily scheduler")
    args = parser.parse_args()

    init_db()

    if args.ingest:
        from ingestion.pipeline import run_ingestion
        sources = [args.source] if args.source else None
        run_ingestion(sources=sources)

    elif args.clean:
        from processing.cleaner import run_cleaning
        run_cleaning()

    elif args.eda:
        from analytics.eda.exploratory import run_eda
        run_eda()

    elif args.hedonic:
        from analytics.hedonic.model import run_all_models
        run_all_models()

    elif args.index:
        from analytics.index.rppi import run_index
        run_index()

    elif args.dashboard:
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run",
                        os.path.join(os.path.dirname(__file__), "dashboard", "app.py")])

    elif args.schedule:
        import schedule, time
        log.info("Scheduler started — daily at 06:00")
        schedule.every().day.at("06:00").do(run_full_pipeline)
        while True:
            schedule.run_pending()
            time.sleep(60)

    else:
        run_full_pipeline()