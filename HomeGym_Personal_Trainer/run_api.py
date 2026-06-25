from src.runtime_bootstrap import bootstrap_runtime

bootstrap_runtime()

import uvicorn


if __name__ == "__main__":
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=False)
