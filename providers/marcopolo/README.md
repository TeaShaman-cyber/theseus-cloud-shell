# MarcoPolo provider adapter

Provider-specific runbooks, scripts, historical failure evidence and canonical runtime rules remain in [marcopolo-cookbook](https://github.com/TeaShaman-cyber/marcopolo-cookbook), especially `rules/workspace.RULES.md` and `marcopolo/README.md`.

Use MarcoPolo only after observed need for its supported connection/credential features or a justified failure of the preferred direct route. Retain known failure classes: control-plane 403/502 is not proof of guest failure, `/workspace` is not a portable path, managed connection credentials cannot be assumed accessible to arbitrary subprocesses, and GitHub read/write authority can differ.

Do not bulk-copy MarcoPolo scripts into Cloud Shell. Classify MOVE/ADAPT/LINK/RETAIN/RETIRE per file and test paths on the new host. Existing CI reusable workflows and downstream references remain authoritative until a verified transition.
