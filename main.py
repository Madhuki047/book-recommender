from src.data.sample_data import (
    build_demo_repository_small,
    build_demo_repository_medium,
)
from src.recommender.engine import RecommenderEngine
from src.evaluation.profiler import PerformanceProfiler


def run_demo_for_dataset(name: str, repo_builder) -> None:
    print(f"\n=== Demo on dataset: {name} ===")

    repo = repo_builder()
    engine = RecommenderEngine(repo)
    profiler = PerformanceProfiler()

    target_user = "Alice"

    metrics = ["cosine", "jaccard"]
    k_values = [1, 2, None]  # None = use all neighbours

    for metric in metrics:
        for k in k_values:
            profile = profiler.time_function(
                engine.recommend_for_user,
                target_user=target_user,
                metric=metric,
                k_neighbours=k,
                max_results=5,
            )

            recommendations = profile.result
            elapsed = profile.elapsed_ms

            print(
                f"\nMetric: {metric:7s}, k = {str(k):>4}, "
                f"time = {elapsed:8.4f} ms"
            )

            if not recommendations:
                print("  (no recommendations)")
            else:
                for book_id, score in recommendations:
                    print(f"  {book_id}: {score:.3f}")


def main() -> None:
    run_demo_for_dataset("SMALL", build_demo_repository_small)
    run_demo_for_dataset("MEDIUM", build_demo_repository_medium)


if __name__ == "__main__":
    main()
