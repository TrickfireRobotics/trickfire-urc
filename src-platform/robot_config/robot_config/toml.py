import tomllib
from typing import Any
import os, sys


def __py_to_cpp(msg: str):
    d: dict[str, str] = {
        "int": "int",
        "float": "double",
        "str": "std::string",
        "list": "std::vector",
        "dict": "std::map",
        "tuple": "std::tuple",
        "set": "std::set",
        "NoneType": "void",
        "bytes": "std::vector<uint8_t>",
        "datetime": "std::chrono::system_clock::time_point",
    }
    try:
        return d[msg]
    except KeyError as _:
        return msg


def __snake_to_camel(msg: str) -> str:
    return msg.split("_")[0] + "".join(item.capitalize() for item in msg.split("_")[1:])


def __snake_to_pascal(msg: str) -> str:
    return "".join(item.capitalize() for item in msg.split("_"))


class Logger:
    @staticmethod
    def warning(msg: str):
        pass

    @staticmethod
    def error(msg: str):
        pass

    @staticmethod
    def info(msg: str):
        pass


def parse_file(filename: str) -> dict[str, Any] | None:
    if not os.path.exists(filename):
        Logger.error(f"Toml file doesn't exist, process failed")
    try:
        with open(filename, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError:
        Logger.error("Failed to decode toml config, please check")
    return None


def __subdict_count(obj: dict | Any) -> int:
    if isinstance(obj, dict):
        return 1 + __subdict_count(obj[next(iter(obj))])
    else:
        return 0


def __get_field_types(tml: dict[str, Any], class_name: str) -> dict[str, str]:

    item_objects: dict[str, str] = {}
    if __subdict_count(tml[class_name]) >= 2:
        for instance in tml[class_name]:
            for field in tml[class_name][instance]:
                item_objects[field] = type(tml[class_name][instance][field]).__name__
    else:
        for field in tml[class_name]:
            item_objects[field] = type(tml[class_name][field]).__name__
    return item_objects


def __generate_cpp_fields(value: Any) -> str:
    # Only strings and bools really need to be touched
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, str):
        return f'"{str(value)}"'
    else:
        return str(value)


def __generate_cpp_class(tml: dict[str, Any], class_name: str) -> str:
    # Atleast 2 subdictionaries means there are multiple objects in a subobject which means
    # Multiple objects, so a list needs to be generated
    c_name = __snake_to_pascal(class_name)
    class_def = ""
    if __subdict_count(tml[class_name]) >= 2:
        item_objects: dict[str, str] = __get_field_types(tml, class_name)

        # Implement struct defs here
        class_def += f"struct {c_name} {{"
        for field, value in item_objects.items():
            class_def += f"\n{__py_to_cpp(value)} {field}{{}};"
        class_def += "\n};\n"

        # Next implement the enum
        class_def += f"\n\nenum class {c_name}Enum {{"
        for i, instance in enumerate(tml[class_name].keys()):
            if i == 0:
                class_def += f"{instance} = 0"
            else:
                class_def += f",{instance}"
        class_def += "};"

        # Next the array
        class_def += f"\n\nconst {c_name} {c_name}List[{len(tml[class_name])}] {{"
        for instance in tml[class_name]:
            class_def += f"{c_name}{{"
            for field in item_objects.keys():
                try:
                    class_def += (
                        f".{field} = {__generate_cpp_fields(tml[class_name][instance][field])},"
                    )
                except Exception as _:
                    pass
            class_def = class_def[:-1]
            class_def += "},"
        class_def = class_def[:-1]
        class_def += "};"

    else:
        class_def += f"""
        class {c_name} final {{
        public:
        """
        for item in tml[class_name]:
            class_def += f"static inline const {__py_to_cpp(type(tml[class_name][item]).__name__)} {item}{{{__generate_cpp_fields(tml[class_name][item])}}};\n"

        class_def += "\n};"
    return class_def


def __generate_cpp_build(tml: dict[str, Any]) -> str:
    cpp_build = f"""
    #ifndef _ROBOT_CONFIG
    #define _ROBOT_CONFIG
    #include <iostream>
    namespace RobotConfig {{

    """
    class_defs: list[str] = []
    for c in tml.keys():
        class_defs.append(__generate_cpp_class(tml, c))

    cpp_build += "\n".join(class_defs)
    cpp_build += f"""
    }};
    #endif
    """
    return cpp_build


def __generate_py_class_definitions(tml: dict[str, Any], class_name: str):
    pass


def __generate_py_build(tml: dict[str, Any]) -> None:
    pass


def main():
    toml_file = sys.argv[1]
    print(toml_file)
    d = parse_file(toml_file)
    if d is None:
        raise RuntimeError(
            f"Toml parser failed to parse the provided file {toml_file}. Please make sure that file exists"
        )
        exit(1)
    d = __generate_cpp_build(d)
    print(d)


if __name__ == "__main__":
    main()
