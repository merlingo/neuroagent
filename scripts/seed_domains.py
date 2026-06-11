from app.domains.registry import DomainRegistry


def main() -> None:
    registry = DomainRegistry.from_default_path()
    print(f"Loaded {len(registry.domains)} domains and {len(registry.agents)} agents.")


if __name__ == "__main__":
    main()
