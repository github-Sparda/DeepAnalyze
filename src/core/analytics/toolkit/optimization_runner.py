"""
Optimization Runner - 优化算法统一入口

提供多种优化算法的统一调用方式。
"""

from __future__ import annotations

from typing import Any, Callable, Literal, Optional

import numpy as np
import pandas as pd


class OptimizationRunner:
    """
    优化算法统一入口

    支持算法:
    - gradient_descent: 梯度下降
    - newton: 牛顿法
    - genetic: 遗传算法
    - particle_swarm: 粒子群优化
    - simulated_annealing: 模拟退火
    - bayesian: 贝叶斯优化
    """

    SUPPORTED_METHODS = ["gradient_descent", "newton", "genetic", "particle_swarm", "simulated_annealing", "bayesian"]

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.optimal_x_: Optional[np.ndarray] = None
        self.optimal_y_: Optional[float] = None
        self.history_: list[float] = []

    def run(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        method: Literal["gradient_descent", "newton", "genetic", "particle_swarm", "simulated_annealing", "bayesian", "auto"] = "auto",
        bounds: tuple[tuple[float, float], ...] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        运行优化算法

        Args:
            func: 目标函数
            x0: 初始点
            method: 优化算法
            bounds: 变量边界
            **kwargs: 其他参数

        Returns:
            优化结果
        """
        if method == "auto":
            n_params = len(x0)
            if n_params <= 10:
                method = "gradient_descent"
            else:
                method = "particle_swarm"

        if method == "gradient_descent":
            return self._run_gradient_descent(func, x0, bounds, **kwargs)
        elif method == "newton":
            return self._run_newton(func, x0, **kwargs)
        elif method == "genetic":
            return self._run_genetic(func, x0, bounds, **kwargs)
        elif method == "particle_swarm":
            return self._run_particle_swarm(func, x0, bounds, **kwargs)
        elif method == "simulated_annealing":
            return self._run_simulated_annealing(func, x0, bounds, **kwargs)
        elif method == "bayesian":
            return self._run_bayesian(func, x0, bounds, **kwargs)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

    def _run_gradient_descent(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: tuple[tuple[float, float], ...] | None,
        **kwargs,
    ) -> dict[str, Any]:
        from scipy.optimize import minimize

        lr = kwargs.pop("lr", 0.01)
        max_iter = kwargs.pop("max_iter", 1000)
        tol = kwargs.pop("tol", 1e-6)

        def gradient_func(x):
            eps = 1e-5
            grad = np.zeros_like(x)
            for i in range(len(x)):
                x_plus = x.copy()
                x_plus[i] += eps
                grad[i] = (func(x_plus) - func(x)) / eps
            return grad

        x = x0.copy()
        self.history_ = []

        for i in range(max_iter):
            grad = gradient_func(x)
            x_new = x - lr * grad

            if bounds is not None:
                x_new = np.clip(x_new, [b[0] for b in bounds], [b[1] for b in bounds])

            f_val = func(x_new)
            self.history_.append(f_val)

            if np.linalg.norm(x_new - x) < tol:
                break

            x = x_new

        self.optimal_x_ = x
        self.optimal_y_ = func(x)

        self.results = {
            "method": "gradient_descent",
            "optimal_x": self.optimal_x_.tolist(),
            "optimal_y": float(self.optimal_y_),
            "n_iterations": len(self.history_),
            "history": self.history_[:100],
            "metrics": {
                "final_value": float(self.optimal_y_),
                "converged": len(self.history_) < max_iter,
            },
        }
        return self.results

    def _run_newton(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        **kwargs,
    ) -> dict[str, Any]:
        from scipy.optimize import minimize

        max_iter = kwargs.pop("max_iter", 100)
        tol = kwargs.pop("tol", 1e-6)

        def hessian_func(x):
            eps = 1e-5
            n = len(x)
            hess = np.zeros((n, n))
            f0 = func(x)
            for i in range(n):
                for j in range(n):
                    x_plus_ij = x.copy()
                    x_plus_ij[i] += eps
                    x_plus_ij[j] += eps
                    x_plus_i = x.copy()
                    x_plus_i[i] += eps
                    x_plus_j = x.copy()
                    x_plus_j[j] += eps
                    hess[i, j] = (func(x_plus_ij) - func(x_plus_i) - func(x_plus_j) + f0) / (eps * eps)
            return hess

        def gradient_func(x):
            eps = 1e-5
            grad = np.zeros_like(x)
            for i in range(len(x)):
                x_plus = x.copy()
                x_plus[i] += eps
                grad[i] = (func(x_plus) - func(x)) / eps
            return grad

        x = x0.copy()
        self.history_ = []

        for i in range(max_iter):
            grad = gradient_func(x)
            try:
                hess = hessian_func(x)
                hess_inv = np.linalg.pinv(hess)
                delta = hess_inv @ grad
            except np.linalg.LinAlgError:
                delta = grad * 0.1

            x_new = x - delta
            f_val = func(x_new)
            self.history_.append(f_val)

            if np.linalg.norm(delta) < tol:
                break

            x = x_new

        self.optimal_x_ = x
        self.optimal_y_ = func(x)

        self.results = {
            "method": "newton",
            "optimal_x": self.optimal_x_.tolist(),
            "optimal_y": float(self.optimal_y_),
            "n_iterations": len(self.history_),
            "history": self.history_[:100],
            "metrics": {
                "final_value": float(self.optimal_y_),
                "converged": len(self.history_) < max_iter,
            },
        }
        return self.results

    def _run_genetic(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: tuple[tuple[float, float], ...] | None,
        **kwargs,
    ) -> dict[str, Any]:
        n_population = kwargs.pop("n_population", 50)
        n_generations = kwargs.pop("n_generations", 100)
        mutation_rate = kwargs.pop("mutation_rate", 0.1)
        crossover_rate = kwargs.pop("crossover_rate", 0.8)
        elitism = kwargs.pop("elitism", 2)

        n_params = len(x0)
        if bounds is None:
            bounds = [(-10, 10) for _ in range(n_params)]

        def random_individual():
            return np.array([np.random.uniform(b[0], b[1]) for b in bounds])

        def crossover(parent1, parent2):
            if np.random.rand() < crossover_rate:
                alpha = np.random.rand()
                return alpha * parent1 + (1 - alpha) * parent2
            return parent1 if np.random.rand() > 0.5 else parent2

        def mutate(individual):
            for i in range(n_params):
                if np.random.rand() < mutation_rate:
                    individual[i] = np.random.uniform(bounds[i][0], bounds[i][1])
            return individual

        population = [random_individual() if i > 0 else x0.copy() for i in range(n_population)]
        self.history_ = []

        for gen in range(n_generations):
            fitness = [func(ind) for ind in population]
            sorted_indices = np.argsort(fitness)

            self.history_.append(float(np.min(fitness)))

            new_population = [population[i] for i in sorted_indices[:elitism]]

            while len(new_population) < n_population:
                parent1, parent2 = np.random.choice(n_population, 2, replace=False)
                child = crossover(population[parent1], population[parent2])
                child = mutate(child)

                for i in range(n_params):
                    child[i] = np.clip(child[i], bounds[i][0], bounds[i][1])

                new_population.append(child)

            population = new_population

        best_idx = np.argmin([func(ind) for ind in population])
        self.optimal_x_ = population[best_idx]
        self.optimal_y_ = func(self.optimal_x_)

        self.results = {
            "method": "genetic",
            "optimal_x": self.optimal_x_.tolist(),
            "optimal_y": float(self.optimal_y_),
            "n_generations": n_generations,
            "history": self.history_[:100],
            "metrics": {
                "final_value": float(self.optimal_y_),
            },
        }
        return self.results

    def _run_particle_swarm(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: tuple[tuple[float, float], ...] | None,
        **kwargs,
    ) -> dict[str, Any]:
        n_particles = kwargs.pop("n_particles", 30)
        n_iterations = kwargs.pop("n_iterations", 100)
        w = kwargs.pop("w", 0.7)
        c1 = kwargs.pop("c1", 1.5)
        c2 = kwargs.pop("c2", 1.5)

        n_params = len(x0)
        if bounds is None:
            bounds = [(-10, 10) for _ in range(n_params)]

        x = np.array([np.random.uniform(b[0], b[1], n_particles) for b in bounds]).T
        for i in range(n_particles):
            if i == 0:
                x[i] = x0.copy()

        v = np.zeros((n_particles, n_params))
        p_best = x.copy()
        p_best_val = np.array([func(x[i]) for i in range(n_particles)])

        g_best_idx = np.argmin(p_best_val)
        g_best = x[g_best_idx].copy()
        g_best_val = p_best_val[g_best_idx]

        self.history_ = []

        for iteration in range(n_iterations):
            for i in range(n_particles):
                r1, r2 = np.random.rand(n_params), np.random.rand(n_params)
                v[i] = w * v[i] + c1 * r1 * (p_best[i] - x[i]) + c2 * r2 * (g_best - x[i])

                x[i] = x[i] + v[i]

                for j in range(n_params):
                    x[i, j] = np.clip(x[i, j], bounds[j][0], bounds[j][1])

                f_val = func(x[i])
                if f_val < p_best_val[i]:
                    p_best[i] = x[i].copy()
                    p_best_val[i] = f_val

                if f_val < g_best_val:
                    g_best = x[i].copy()
                    g_best_val = f_val

            self.history_.append(float(g_best_val))

        self.optimal_x_ = g_best
        self.optimal_y_ = g_best_val

        self.results = {
            "method": "particle_swarm",
            "optimal_x": self.optimal_x_.tolist(),
            "optimal_y": float(self.optimal_y_),
            "n_iterations": n_iterations,
            "history": self.history_,
            "metrics": {
                "final_value": float(self.optimal_y_),
            },
        }
        return self.results

    def _run_simulated_annealing(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: tuple[tuple[float, float], ...] | None,
        **kwargs,
    ) -> dict[str, Any]:
        n_iterations = kwargs.pop("n_iterations", 1000)
        initial_temp = kwargs.pop("initial_temp", 100.0)
        cooling_rate = kwargs.pop("cooling_rate", 0.95)

        n_params = len(x0)
        if bounds is None:
            bounds = [(-10, 10) for _ in range(n_params)]

        x = x0.copy()
        f_val = func(x)
        best_x = x.copy()
        best_val = f_val

        self.history_ = [float(f_val)]
        temp = initial_temp

        for i in range(n_iterations):
            delta = np.random.randn(n_params) * temp / initial_temp
            x_new = x + delta

            for j in range(n_params):
                x_new[j] = np.clip(x_new[j], bounds[j][0], bounds[j][1])

            f_new = func(x_new)
            delta_f = f_new - f_val

            if delta_f < 0 or np.random.rand() < np.exp(-delta_f / temp):
                x = x_new
                f_val = f_new

                if f_val < best_val:
                    best_x = x.copy()
                    best_val = f_val

            temp *= cooling_rate
            self.history_.append(float(f_val))

        self.optimal_x_ = best_x
        self.optimal_y_ = best_val

        self.results = {
            "method": "simulated_annealing",
            "optimal_x": self.optimal_x_.tolist(),
            "optimal_y": float(self.optimal_y_),
            "n_iterations": n_iterations,
            "history": self.history_[:100],
            "metrics": {
                "final_value": float(self.optimal_y_),
            },
        }
        return self.results

    def _run_bayesian(
        self,
        func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: tuple[tuple[float, float], ...] | None,
        **kwargs,
    ) -> dict[str, Any]:
        try:
            from skopt import gp_minimize
            from skopt.space import Real
        except ImportError:
            return {"status": "error", "message": "scikit-optimize not installed"}

        n_calls = kwargs.pop("n_calls", 50)
        n_params = len(x0)

        if bounds is None:
            bounds = [(-10, 10) for _ in range(n_params)]

        space = [Real(b[0], b[1]) for b in bounds]

        def wrapper(x):
            return func(np.array(x))

        result = gp_minimize(wrapper, space, n_calls=n_calls, random_state=42, verbose=False)

        self.optimal_x_ = np.array(result.x)
        self.optimal_y_ = result.fun
        self.history_ = list(result.func_vals)

        self.results = {
            "method": "bayesian",
            "optimal_x": self.optimal_x_.tolist(),
            "optimal_y": float(self.optimal_y_),
            "n_calls": n_calls,
            "history": [float(x) for x in self.history_],
            "metrics": {
                "final_value": float(self.optimal_y_),
            },
        }
        return self.results

    def get_summary(self) -> dict[str, Any]:
        """获取结果摘要"""
        if not self.results:
            return {"status": "error", "message": "Run optimization first"}

        return {
            "method": self.results.get("method"),
            "optimal_y": self.results.get("optimal_y"),
            "metrics": self.results.get("metrics", {}),
        }