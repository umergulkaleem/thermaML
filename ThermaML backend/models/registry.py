from models.linear_regression import create_linear_regression_model
from models.random_forest import create_random_forest_model


MODEL_FACTORIES = {
    "linear_regression": create_linear_regression_model,
    "random_forest": create_random_forest_model,
}

MODEL_STATUS = {
    "lightweight_gnn": {
        "status": "not_available",
        "reason": "PyTorch and PyTorch Geometric dependencies are unavailable.",
    }
}


def get_model_factory(model_name):
    try:
        return MODEL_FACTORIES[model_name]
    except KeyError as error:
        raise ValueError(f"Unknown model: {model_name}") from error


def get_available_models():
    return sorted(MODEL_FACTORIES)


def get_model_status():
    return MODEL_STATUS.copy()
