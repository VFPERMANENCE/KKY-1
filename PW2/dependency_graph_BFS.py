from collections import deque, defaultdict
from typing import Set, Dict, List, Optional

class DependencyGraph:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.visited = set()
        self.cycles = []
    
    def add_dependency(self, package: str, dependency: str):
        """Добавляет зависимость в граф"""
        if dependency:  # Игнорируем пустые зависимости
            self.graph[package].add(dependency)
    
    def build_graph_bfs(self, start_package: str, get_dependencies_func, exclude_filter: Optional[str] = None, max_depth: int = 10):
        """
        Строит граф зависимостей с помощью BFS
        
        Args:
            start_package: начальный пакет
            get_dependencies_func: функция для получения зависимостей пакета
            exclude_filter: подстрока для исключения пакетов
            max_depth: максимальная глубина поиска
        """
        queue = deque([(start_package, 0)])  # (package, depth)
        self.visited = set([start_package])
        self.cycles = []
        
        while queue:
            current_package, depth = queue.popleft()
            
            if depth >= max_depth:
                print(f"Достигнута максимальная глубина {max_depth} для пакета {current_package}")
                continue
            
            try:
                dependencies = get_dependencies_func(current_package)
                
                for dep in dependencies:
                    # Применяем фильтр исключения
                    if exclude_filter and exclude_filter in dep:
                        print(f"Пропуск пакета {dep} (фильтр: {exclude_filter})")
                        continue
                    
                    self.add_dependency(current_package, dep)
                    
                    # Проверяем циклические зависимости
                    if dep in self.graph and current_package in self.graph[dep]:
                        cycle = (current_package, dep)
                        if cycle not in self.cycles and (dep, current_package) not in self.cycles:
                            self.cycles.append(cycle)
                            print(f"  Обнаружена циклическая зависимость: {current_package} <-> {dep}")
                    
                    # Добавляем в очередь для дальнейшего обхода
                    if dep not in self.visited:
                        self.visited.add(dep)
                        queue.append((dep, depth + 1))
                        
            except Exception as e:
                print(f"Ошибка при обработке пакета {current_package}: {e}")
    
    def get_all_dependencies(self, package: str) -> Set[str]:
        """Получает все транзитивные зависимости пакета"""
        if package not in self.graph:
            return set()
        
        all_deps = set()
        queue = deque([package])
        visited = set([package])
        
        while queue:
            current = queue.popleft()
            for dep in self.graph.get(current, set()):
                if dep not in visited:
                    visited.add(dep)
                    all_deps.add(dep)
                    queue.append(dep)
        
        return all_deps
    
    def has_cycles(self) -> bool:
        """Проверяет наличие циклических зависимостей"""
        return len(self.cycles) > 0
    
    def get_cycles(self) -> List[tuple]:
        """Возвращает список циклических зависимостей"""
        return self.cycles
    
    def display_graph(self, start_package: str):
        """Отображает граф в виде дерева"""
        print(f"\nГраф зависимостей для {start_package}:")
        print("=" * 50)
        
        if not self.graph:
            print("Граф пуст")
            return
        
        visited = set()
        
        def display_node(package: str, level: int = 0, prefix: str = ""):
            if package in visited:
                print(f"{prefix}└── {package} (цикл)")
                return
            
            visited.add(package)
            dependencies = sorted(self.graph.get(package, set()))
            
            for i, dep in enumerate(dependencies):
                is_last = i == len(dependencies) - 1
                
                if level == 0:
                    connector = "┌── " if i == 0 else "├── " if not is_last else "└── "
                else:
                    connector = "├── " if not is_last else "└── "
                
                print(f"{prefix}{connector}{dep}")
                
                if dep in self.graph:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    display_node(dep, level + 1, new_prefix)
        
        print(f"┌── {start_package}")
        display_node(start_package, 1, "")
        
        if self.cycles:
            print(f"\n  Найденные циклические зависимости:")
            for cycle in self.cycles:
                print(f"   {cycle[0]} <-> {cycle[1]}")
        else:
            print(f"\n Циклических зависимостей нет")