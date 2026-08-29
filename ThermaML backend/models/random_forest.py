from sklearn.ensemble import RandomForestRegressor


def create_random_forest_model():
    return RandomForestRegressor(
        n_estimators=200,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
