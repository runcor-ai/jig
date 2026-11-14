import pytest

from jig.parser import ParseError, Ref, parse

CMDS = {"specify", "build", "test", "verify", "research"}


def test_parses_script_with_bindings_and_literals():
    src = '''
spec = specify("A pong game",
               constraints=["React", "no backend"], id="PONG-001")  # comment
build(spec, notes=None)
test(spec, run=["npm test"], timeout_s=-1)
research(spec.output.title, question=spec.id)
'''
    st = parse(src, CMDS)
    assert [s.command for s in st] == ["specify", "build", "test", "research"]
    assert st[0].bind == "spec" and st[0].kwargs["constraints"] == ["React", "no backend"]
    assert st[1].target == Ref("spec") and st[1].kwargs == {"notes": None}
    assert st[2].kwargs["timeout_s"] == -1
    assert st[3].target == Ref("spec", ("output", "title"))
    assert st[3].kwargs["question"] == Ref("spec", ("id",))
    assert st[0].line == 2


def test_external_variables_and_json_style_literals():
    st = parse('research(topic, question=q, x={"a": [1, true, null]})', CMDS, predefined={"topic", "q"})
    assert st[0].target == Ref("topic") and st[0].kwargs["x"] == {"a": [1, True, None]}


@pytest.mark.parametrize("src,msg", [
    ('import os', "not allowed"),
    ('os.system("rm -rf /")', "unknown method 'system'"),      # only data-type methods exist
    ('spec = specify("x")\nspec.output.run()', "unknown method 'run'"),
    ('xs = []\nxs.__class__()', "starting with '_'"),
    ('specify(__import__("os"))', "unknown command '__import__'"),
    ('specify(2 ** 64)', "not supported"),
    ('specify(f"{1!r}")', "conversions are not supported"),
    ('specify([x for x in y])', "unsupported expression"),
    ('specify(lambda: 1)', "unsupported expression"),
    ('specify("x")(1)', "bare identifier"),
    ('x = len(specify("x"))', "must be a statement of its own"),
    ('if verify("A-001").status:\n  pass', "dotted references must start"),
    ('if len(verify("A-001")):\n  pass', "must be a statement of its own"),
    ('n += 1', "undefined variable"),
    ('list = []', "reserved"),
    ('spec = specify("x")\nbuild(spec.__class__)', "starting with '_'"),
    ('spec = specify("x")\nbuild(spec._secret)', "starting with '_'"),
    ('_x = specify("x")', "starting with '_'"),
    ('specify("x").output', "must be a command call"),
    ('build(specify("x").id)', "dotted references must start"),
    ('build(undefined_var)', "undefined variable"),
    ('build(missing.id)', "undefined variable"),
    ('eval("1")', "unknown command"),
    ('specify("a", "b")', "at most one positional"),
    ('specify(*args)', "star-arguments"),
    ('specify(**kw)', "**kwargs"),
    ('x.y = specify("a")', "single name"),
    ('for x in y: specify(x)', "undefined variable"),
    ('def f(): pass', "not allowed"),
    ('class A: pass', "not allowed"),
    ('with x: pass', "not allowed"),
    ('try:\n  pass\nexcept:\n  pass', "not allowed"),
    ('del x', "not allowed"),
    ('global x', "not allowed"),
    ('x = 1\nwhile x:\n  pass\nelse:\n  pass', "while ... else"),
    ('break', "outside a loop"),
    ('specify((y := 1))', "unsupported expression"),
    ('x = [1]\nx[0:2] = [3]', "assignment target"),
    ('specify(', "syntax error"),
    ('specify(a=1, a=2)', "duplicate parameter"),
])
def test_rejects_unsafe_or_invalid(src, msg):
    with pytest.raises(ParseError) as e:
        parse(src, CMDS)
    assert msg in str(e.value)
