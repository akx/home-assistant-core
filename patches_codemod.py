import libcst as cst
from libcst.codemod import VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor


def get_patch_call_from_with_item(item: cst.WithItem) -> cst.Call | None:
    if item.asname:  # ignore node with `as`
        return None
    if not isinstance(item.item, cst.Call):
        return None
    if isinstance(item.item.func, cst.Name):
        if item.item.func.value == "patch":
            return item.item
    return None


class ConvertPatchWithCommand(VisitorBasedCodemodCommand):
    def leave_With(
        self,
        original_node: cst.With,
        updated_node: cst.With,
    ) -> cst.With:
        patch_calls = [
            get_patch_call_from_with_item(item) for item in original_node.items
        ]
        print(patch_calls)
        if any(item is None for item in patch_calls):
            return updated_node
        if len(patch_calls) == 1:
            return updated_node

        patch_call_argsets = [pc.args for pc in patch_calls]

        patched_names = {}

        for argset in patch_call_argsets:
            name = None
            args = {}
            for i, arg in enumerate(argset):
                assert isinstance(arg, cst.Arg)
                if i == 0:
                    assert isinstance(arg.value, cst.SimpleString)
                    name = arg.value.evaluated_value
                else:
                    assert arg.keyword
                    args[arg.keyword.value] = arg.value
                # if arg.keyword:
                #     return updated_node
                # if not isinstance(arg.value, cst.SimpleString):
                #     return updated_node
            patched_names[name] = args

        # Replace with a single `patches` call

        patches_args = []
        for name, pargs in sorted(patched_names.items()):
            assert not pargs
            patches_args.append(cst.parse_expression(repr(name)))

        new_items = [
            cst.WithItem(
                item=cst.Call(
                    func=cst.Name("patches"),
                    args=[
                        cst.Arg(
                            value=cst.List(
                                elements=[
                                    cst.Element(value=arg, comma=cst.Comma())
                                    for arg in patches_args
                                ]
                            ),
                            comma=cst.Comma(),
                        )
                    ],
                ),
                asname=None,
            ),
        ]

        updated_node = updated_node.with_changes(items=new_items)

        AddImportsVisitor.add_needed_import(
            self.context,
            "tests.common",
            "patches",
        )
        return updated_node
