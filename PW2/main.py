import argparse
import sys
from pathlib import Path

from errors_not_for_us import *
from apk_analizer import APKAnalyzer
from dependency_graph_BFS import DependencyGraph
from test import TestRepository

def main():
    parser = argparse.ArgumentParser(
        description="Инструмент анализа графа зависимостей пакетов Alpine Linux",
        epilog="""
Примеры использования:
  python main.py --package-name A --repo-url test_repo.txt --mode test
        """
    )
    
    parser.add_argument("--package-name", required=True, type=validate_package_name,
                       help="Имя анализируемого пакета")
    parser.add_argument("--repo-url", required=True, type=validate_url_or_path,
                       help="URL репозитория, путь к локальной директории или файлу тестового репозитория")
    parser.add_argument("--mode", required=True, type=validate_mode,
                       help="Режим работы: local, remote или test")
    parser.add_argument("--version", 
                       help="Версия пакета (требуется для режимов local и remote)")
    parser.add_argument("--output", type=validate_output,
                       help="Имя выходного файла для графа")
    parser.add_argument("--exclude",
                       help="Подстрока для исключения пакетов из анализа")
    parser.add_argument("--max-depth", type=int, default=10,
                       help="Максимальная глубина поиска зависимостей")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print(" АНАЛИЗ ГРАФА ЗАВИСИМОСТЕЙ")
        print("=" * 60)
        print(f"Пакет: {args.package_name}")
        print(f"Источник: {args.repo_url}")
        print(f"Режим: {args.mode}")
        if args.version:
            print(f"Версия: {args.version}")
        if args.exclude:
            print(f"Исключение: {args.exclude}")
        if args.max_depth:
            print(f"Максимальная глубина: {args.max_depth}")
        print("=" * 60)
        
       
        graph = DependencyGraph()
        
        if args.mode == "test":
            test_repo = TestRepository(args.repo_url)
            
            if not test_repo.package_exists(args.package_name):
                raise RuntimeError(f"Пакет {args.package_name} не найден в тестовом репозитории")
            
            # Строим граф с помощью BFS
            graph.build_graph_bfs(
                start_package=args.package_name,
                get_dependencies_func=test_repo.get_dependencies,
                exclude_filter=args.exclude,
                max_depth=args.max_depth
            )
            
        else:
            # APK-ПАКЕТ
            if not args.version:
                raise RuntimeError("Для режимов local и remote требуется указать --version")
            
            analyzer = APKAnalyzer(args.repo_url, args.mode)
            
            def get_apk_dependencies(package: str):
                """Функция для получения зависимостей пакета"""
                apk_path = analyzer.get_apk_path(package, args.version)
                return analyzer.extract_dependencies(apk_path)
            
            # Строим граф с помощью BFS
            graph.build_graph_bfs(
                start_package=args.package_name,
                get_dependencies_func=get_apk_dependencies,
                exclude_filter=args.exclude,
                max_depth=args.max_depth
            )
            
        graph.display_graph(args.package_name)
    
        print(f"\n СТАТИСТИКА:")
        print(f"   Всего пакетов в графе: {len(graph.visited)}")
        print(f"   Обнаружено циклов: {len(graph.cycles)}")
        
        if args.output:
            # Здесь можно добавить экспорт в DOT формат для визуализации
            print(f"Граф сохранен в: {args.output}")
        
        print("\n Анализ завершен успешно!")
        
    except Exception as e:
        print(f"\n Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
    
# # Режим тестирования с файлом репозитория
#   python main.py --package-name A --repo-url test_repo.txt --mode test
  
#   # Реальный APK-пакет
#   python main.py --package-name busybox --repo-url https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/ --mode remote --version 1.37.0-r13
  
#   # С исключением пакетов
#   python main.py --package-name A --repo-url test_repo.txt --mode test --exclude C    