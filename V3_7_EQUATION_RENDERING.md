# Version 3.7 — Clear Equations and Physics QA

- Quick Solver prompts require valid LaTeX inside `$$` delimiters.
- Fenced `math`/`latex` blocks are converted to supported display delimiters.
- The Gradio Chatbot explicitly enables display and inline LaTeX delimiters.
- Long electric-field and magnetic-field questions receive a second science review.
- The reviewer checks signed charge, restoring-force direction, units, dimensions,
  roots and consistency between intermediate equations and the final answer.

For the charged-ring SHM problem, the expected verified formulas are:

$$
T=2\pi\sqrt{\frac{4\pi\varepsilon_0mR^3}{Qq}}
$$

$$
v_{\max}=x_0\sqrt{\frac{Qq}{4\pi\varepsilon_0mR^3}}
$$

The ring mass does not enter because the ring is fixed.
