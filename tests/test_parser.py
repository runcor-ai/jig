import pytest

from lattice.parser import ParseError, Ref, parse

CMDS = {"requirement", "design", "build", "review", "verify", "test"}


def test_parses_spec_script():
    src = '''
requirement("Build a customer management application",
            stack=["Java", "React", "PostgreSQL"],
            standard="enterprise")
design("CRM-001")  # comment
review("CRM-001", criteria=["security", "architecture"])
verify("CRM-001", against="requirements")
'''
    st = parse(src, CMDS)
    assert [s.command for s in st] == ["requirement", "design", "review", "verify"]
    assert st[0].target == "Build a customer management application"
    assert st[0].kwargs == {"stack": ["Java", "React", "PostgreSQL"], "standard": "enterprise"}
    assert st[2].kwargs["criteria"] == ["security", "architecture"]
    assert st[0].line == 2


def test_assignment_and_reference():
    st = parse('crm = requirement("x")\ndesign(crm)\n', CMDS)
    assert st[0].bind == "crm"
    assert st[1].target == Ref("crm")


def test_literals():
    st = parse('build("A-001", budget_usd=-1.5, notes=None, x={"a": [1, true]})', None)
    assert st[0].kwargs == {"budget_usd": -1.5, "notes": None, "x": {"a": [1, True]}}


@pytest.mark.parametrize("src,msg", [
    ('import os', "not allowed"),
    ('os.system("rm -rf /")', "bare identifier"),
    ('design(__import__("os"))', "only literals"),
    ('design("a" + "b")', "only literals"),
    ('design(f"{x}")', "only literals"),
    ('design([x for x in y])', "only literals"),
    ('design(lambda: 1)', "only literals"),
    ('eval("1")', "unknown command"),
    ('design("a", "b")', "at most one positional"),
    ('design(*args)', "star-arguments"),
    ('design(**kw)', "**kwargs"),
    ('design(undefined_var)', "undefined variable"),
    ('x.y = design("a")', "single name"),
    ('design("a")[0]', "must be a command call"),
    ('design(', "syntax error"),
    ('design(a=1, a=2)', "duplicate parameter"),
])
def test_rejects_unsafe_or_invalid(src, msg):
    with pytest.raises(ParseError) as e:
        parse(src, CMDS)
    assert msg in str(e.value)
