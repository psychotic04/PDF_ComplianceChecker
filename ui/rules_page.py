import streamlit as st

from services import db_service


def render_rules_page() -> None:
    st.header("Compliance Rules")

    with st.form("add-rule-form", clear_on_submit=True):
        st.subheader("Add Rule")
        rule_name = st.text_input("Rule Name")
        rule_description = st.text_area("Rule Description", height=100)
        submitted = st.form_submit_button("Save Rule", type="primary")
        if submitted:
            if not rule_name.strip() or not rule_description.strip():
                st.warning("Rule name and description are required.")
            else:
                db_service.add_rule(rule_name.strip(), rule_description.strip())
                st.success("Rule added.")
                st.rerun()

    st.divider()
    st.subheader("Existing Rules")
    rules = db_service.list_rules()
    if not rules:
        st.info("No compliance rules found.")
        return

    for rule in rules:
        with st.expander(rule["rule_name"]):
            with st.form(f"edit-rule-{rule['id']}"):
                updated_name = st.text_input("Rule Name", value=rule["rule_name"], key=f"name-{rule['id']}")
                updated_description = st.text_area(
                    "Rule Description",
                    value=rule["rule_description"],
                    height=120,
                    key=f"description-{rule['id']}",
                )
                col1, col2 = st.columns([1, 1])
                save = col1.form_submit_button("Save Rule")
                delete = col2.form_submit_button("Delete Rule")

                if save:
                    db_service.update_rule(rule["id"], updated_name.strip(), updated_description.strip())
                    st.success("Rule updated.")
                    st.rerun()

                if delete:
                    db_service.delete_rule(rule["id"])
                    st.success("Rule deleted.")
                    st.rerun()
