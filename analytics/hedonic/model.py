"""
analytics/hedonic/model.py
Phase 7 & 8 — Hedonic Model Design and Variable Selection
Method: Semi-log OLS — ln(price) ~ structural + location + time dummies
This is the IMF/Eurostat recommended approach for RPPI from web data.

Model: ln(P_it) = α + β·X_it + Σγ_t·D_t + ε_it
Where:
  P_it = listing price of property i at time t
  X_it = vector of structural and location characteristics
  D_t  = time dummy variables (base period = 2024-Q1)
  γ_t  = estimated price change relative to base period
"""
import numpy as np
import pandas as pd
import joblib
import statsmodels.api as sm
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder
from database.models import SessionLocal, CleanListing
from config.settings import MODEL_DIR, EXPORT_DIR, HEDONIC, INDEX
from utils.logger import log


def load_data(transaction: str = "location") -> pd.DataFrame:
    session = SessionLocal()
    rows = session.query(CleanListing).filter(
        CleanListing.transaction == transaction,
        CleanListing.price.isnot(None),
        CleanListing.log_price.isnot(None),
        CleanListing.city.isnot(None),
    ).all()
    session.close()
    df = pd.DataFrame([{
        "log_price":    r.log_price,
        "price":        r.price,
        "surface":      r.surface,
        "rooms":        r.rooms,
        "property_type":r.property_type,
        "city":         r.city,
        "year_quarter": r.year_quarter,
        "neighborhood": r.neighborhood,
    } for r in rows])
    log.info(f"[hedonic] Loaded {len(df)} records for transaction={transaction}")
    return df


def prepare_features(df: pd.DataFrame, base_period: str = "2024-Q1"):
    """
    Build design matrix X for semi-log OLS.
    Categorical variables → dummy encoding.
    Time dummies → base period dropped (reference category).
    """
    df = df.copy().dropna(subset=["log_price"])

    # Fill missing structural variables with median
    df["surface"] = df["surface"].fillna(df["surface"].median())
    df["rooms"]   = df["rooms"].fillna(df["rooms"].median())

    # Dummy encode categoricals
    cat_cols = ["property_type", "city"]
    df_dummies = pd.get_dummies(df[cat_cols], drop_first=True, prefix=cat_cols)

    # Time dummies — drop base period
    time_dummies = pd.get_dummies(df["year_quarter"], prefix="T")
    base_col = f"T_{base_period}"
    if base_col in time_dummies.columns:
        time_dummies = time_dummies.drop(columns=[base_col])

    # Assemble design matrix
    numeric = df[["surface","rooms"]].reset_index(drop=True)
    X = pd.concat([numeric, df_dummies.reset_index(drop=True),
                   time_dummies.reset_index(drop=True)], axis=1)
    X = sm.add_constant(X)
    y = df["log_price"].reset_index(drop=True)

    return X, y, df["year_quarter"].reset_index(drop=True)


def run_ols(X: pd.DataFrame, y: pd.Series):
    """Fit OLS model and return results."""
    model = sm.OLS(y, X.astype(float)).fit(cov_type="HC3")  # heteroskedasticity-robust SE
    return model


def extract_time_coefficients(model, base_period: str = "2024-Q1") -> pd.DataFrame:
    """
    Phase 9 — Extract time dummy coefficients → price index.
    γ_t = ln(P_t / P_base) → index_t = 100 × exp(γ_t)
    """
    params = model.params
    pvalues = model.pvalues
    conf    = model.conf_int()

    time_params = {
        col: {"coeff": params[col], "pvalue": pvalues[col],
              "ci_lo": conf.loc[col, 0], "ci_hi": conf.loc[col, 1]}
        for col in params.index if col.startswith("T_")
    }

    # Add base period
    time_params[f"T_{base_period}"] = {
        "coeff": 0.0, "pvalue": 1.0, "ci_lo": 0.0, "ci_hi": 0.0
    }

    rows = []
    for col, vals in sorted(time_params.items()):
        period = col.replace("T_", "")
        idx    = round(100 * np.exp(vals["coeff"]), 2)
        ci_lo  = round(100 * np.exp(vals["ci_lo"]), 2)
        ci_hi  = round(100 * np.exp(vals["ci_hi"]), 2)
        rows.append({
            "year_quarter": period,
            "gamma":        round(vals["coeff"], 4),
            "index_value":  idx,
            "ci_lower":     ci_lo,
            "ci_upper":     ci_hi,
            "pvalue":       round(vals["pvalue"], 4),
        })

    return pd.DataFrame(rows).sort_values("year_quarter").reset_index(drop=True)


def run_hedonic(transaction: str = "location"):
    log.info(f"=== Phase 7-8-9: Hedonic Model ({transaction}) ===")
    df = load_data(transaction)
    if len(df) < 50:
        log.warning(f"[hedonic] Not enough data ({len(df)} rows). Need ≥50.")
        return None

    X, y, periods = prepare_features(df, INDEX["base_period"])
    log.info(f"[hedonic] Design matrix: {X.shape[0]} obs × {X.shape[1]} variables")

    model = run_ols(X, y)

    # Model diagnostics
    log.info(f"\n  Model diagnostics:")
    log.info(f"    R²           : {model.rsquared:.4f}")
    log.info(f"    Adj. R²      : {model.rsquared_adj:.4f}")
    log.info(f"    F-statistic  : {model.fvalue:.2f} (p={model.f_pvalue:.4f})")
    log.info(f"    N obs        : {int(model.nobs)}")
    log.info(f"    AIC          : {model.aic:.2f}")
    log.info(f"    BIC          : {model.bic:.2f}")

    # Structural variable coefficients
    log.info(f"\n  Key structural coefficients (semi-log interpretation):")
    for var in ["surface", "rooms", "const"]:
        if var in model.params:
            coeff = model.params[var]
            pval  = model.pvalues[var]
            sig   = "***" if pval < 0.01 else ("**" if pval < 0.05 else ("*" if pval < 0.1 else ""))
            pct   = (np.exp(coeff) - 1) * 100
            log.info(f"    {var:<20}: β={coeff:.4f} → {pct:+.1f}% per unit {sig}")

    # Extract price index
    index_df = extract_time_coefficients(model, INDEX["base_period"])
    log.info(f"\n  Price Index ({transaction}, base={INDEX['base_period']}=100):")
    log.info(f"  {'Period':<12} {'Index':>8} {'CI 95%':>16} {'γ':>8} {'p-val':>8}")
    log.info(f"  {'-'*55}")
    for _, row in index_df.iterrows():
        sig = "***" if row.pvalue < 0.01 else ("**" if row.pvalue < 0.05 else "")
        log.info(f"  {row.year_quarter:<12} {row.index_value:>8.2f} "
                 f"  [{row.ci_lower:.1f}–{row.ci_upper:.1f}] "
                 f"{row.gamma:>8.4f} {row.pvalue:>7.4f} {sig}")

    # Save outputs
    ts   = datetime.utcnow().strftime("%Y%m%d")
    path = EXPORT_DIR / f"rppi_{transaction}_{ts}.csv"
    index_df.to_csv(path, index=False)
    log.success(f"[hedonic] RPPI saved → {path}")

    # Save model
    joblib.dump(model, MODEL_DIR / f"hedonic_{transaction}.pkl")

    return model, index_df


def run_all_models():
    results = {}
    for txn in ["location", "vente"]:
        out = run_hedonic(txn)
        if out:
            results[txn] = out
    return results
