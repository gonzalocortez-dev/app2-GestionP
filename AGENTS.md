# Reflex conventions

- Reflex is pure Python that compiles to a React frontend. Do NOT write JS, HTML, or JSX.
- Components are function calls that return components; pass props as keyword args.
- NEVER use plain Python control flow on state Vars inside the render tree.
  No `if`, `for`, `len()`, or f-strings over a Var — use `rx.cond`, `rx.foreach`,
  and Var operators instead.
- State lives in `rx.State` subclasses. State only mutates inside event-handler
  methods — never at module load or render time. Derived values use `@rx.var`.
- Event handlers may be `async` and may `yield` to push intermediate UI updates.
- `.web/` is generated output — never edit or commit it. `rxconfig.py` is the config entry point.
- Database credentials come from `DATABASE_URL`. Never hardcode secrets.
