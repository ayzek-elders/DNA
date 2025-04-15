Firstly install the UV package manager (it is much faster than pip)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex
```

```MacOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

or you can use not sure`pip install uv`

But you must run the terminal or visual studio code with adminisitrive privillages

after that you have to write below code which will install all the dependencies.

```
uv sync
```

then you can activate your virtual env.
