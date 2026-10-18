"""Launch the LabelWise API consumed by the Next.js frontend."""

from dotenv import load_dotenv

load_dotenv()

import uvicorn


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
