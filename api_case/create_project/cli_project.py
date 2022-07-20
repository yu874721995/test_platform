# encoding=utf-8
import argparse, sys, os
from loguru import logger
from api_case.create_project.sample_code import *


def init_parser_scaffold(subparsers):
    sub_parser_scaffold = subparsers.add_parser(
        "startproject", help="Create a new project with template structure."
    )
    sub_parser_scaffold.add_argument(
        "project_name", type=str, nargs="?", help="Specify new project name."
    )

    return sub_parser_scaffold


def create_scaffold(project_name):
    """ Create scaffold with specified project name."""
    if os.path.isdir(project_name):
        logger.warning(
            f"Project folder {project_name} exists, please specify a new project name."
        )
        return 1
    elif os.path.isfile(project_name):
        logger.warning(
            f"Project name {project_name} conflicts with existed file, please specify a new one."
        )
        return 1

    logger.info(f"Create new project: {project_name}")
    print(f"Project root dir: {os.path.join(os.getcwd(), project_name)}\n")

    def create_folder(path):
        os.makedirs(path)
        msg = f"Created folder: {path}"
        print(msg)

    def create_file(path, file_content=""):
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
        msg = f"Created file: {path}"
        print(msg)
    create_folder(project_name)
    create_folder(os.path.join(project_name, "fixtures"))
    create_folder(os.path.join(project_name, "test_case"))
    create_folder(os.path.join(project_name, "test_case_group"))
    create_folder(os.path.join(project_name, "test_cases"))
    create_folder(os.path.join(project_name, "test_cases_group"))
    # create_folder(os.path.join(project_name, "reports"))
    # create_folder(os.path.join(project_name, "reports"))

    create_file(os.path.join(project_name, "conf.yaml"), conf_yaml_content)
    create_file(os.path.join(project_name, "conftest.py"), conftest_content)
    create_file(os.path.join(project_name, "pytest.ini"), pytest_ini_content)
    create_file(os.path.join(project_name, "fixtures", "__init__.py"))
    # 创建项目时默认写入的 fixture_env_vars 文件
    create_file(os.path.join(project_name, "fixtures", "fixture_env_vars.py"), fixture_env_vars_content)
    create_file(os.path.join(project_name, "test_case", "__init__.py"))
    create_file(os.path.join(project_name, "test_case_group", "__init__.py"))
    create_file(os.path.join(project_name, "test_cases", "__init__.py"))
    create_file(os.path.join(project_name, "test_cases_group", "__init__.py"))


def main_scaffold(args):
    sys.exit(create_scaffold(args.project_name))


def main():
    """Parse command line options and run commands.
    """
    parser = argparse.ArgumentParser(description="创建pytest测试项目")
    parser.add_argument(
        "-V", "--version", dest="version", action="store_true", help="show version"
    )
    subparsers = parser.add_subparsers(help="sub-command help")
    sub_parser_scaffold = init_parser_scaffold(subparsers)

    if len(sys.argv) == 1:
        # run_pytest
        parser.print_help()
        sys.exit(0)
    elif len(sys.argv) == 2:
        # print help for sub-commands
        if sys.argv[1] in ["-V", "--version"]:
            # run_pytest -V
            print("v1.0")
        elif sys.argv[1] in ["-h", "--help"]:
            # run_pytest -h
            parser.print_help()
        elif sys.argv[1] == "startproject":
            # run_pytest startproject
            sub_parser_scaffold.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.version:
        print("v1.0")
        sys.exit(0)

    if sys.argv[1] == "startproject":
        main_scaffold(args)


if __name__ == '__main__':
    main()
