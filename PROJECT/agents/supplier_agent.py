import re

import pandas as pd
from PROJECT.models.supplier_models import SupplierResult

SUPPLIER_NAME_STOPWORDS = (
    r"details?|info(?:rmation)?|data|reliability|performance|"
    r"schedule|deliver(?:y|ies)|shipments?|dependency|risk"
)


class SupplierAgent:

    def __init__(self, Schedule_df, Info_df):
        self.Schedule_df = Schedule_df
        self.Info_df = Info_df

    @staticmethod
    def _normalize(text):
        if text is None:
            return ""
        return str(text).strip().lower()

    def get_supplier_schedule(self, supplier_name):

        target = self._normalize(supplier_name)

        supplier_df = (
            self.Schedule_df[
                self.Schedule_df["Suppplier_name"]
                .astype(str)
                .str.strip()
                .str.lower()
                == target
            ]
            .copy()
        )

        supplier_df["Shipment_qty"] = pd.to_numeric(
            supplier_df["Shipment_qty"],
            errors="coerce"
        )

        if supplier_df.empty:
            return None

        return supplier_df

    def get_supplier_tanks(self, supplier_name):

        target = self._normalize(supplier_name)

        names = (
            self.Info_df["Suppplier_name"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        tanks = (
            self.Info_df[
                names.str.contains(
                    re.escape(target),
                    na=False
                )
            ]["tank_id"]
            .unique()
            .tolist()
        )

        return tanks

    def get_supplier_count(self, supplier_name):

        tanks = self.get_supplier_tanks(supplier_name)
        return len(tanks)

    def get_supplier_for_tank(self, tank_id):

        rows = self.Info_df[
            self.Info_df["tank_id"] == tank_id
        ]

        if rows.empty:
            return None

        supplier_field = rows.iloc[0].get("Suppplier_name")

        if pd.isna(supplier_field) or not str(supplier_field).strip():
            return None

        first_supplier = str(supplier_field).split(",")[0].strip()

        return first_supplier

    def extract_tank_id(self, question: str):

        match = re.search(r"tank\s*(\d+)", question, re.IGNORECASE)

        if match:
            return f"Tank {match.group(1)}"

        return None

    def calculate_total_shipped_qty(self, Schedule_df):
        return (
            Schedule_df["Shipment_qty"]
            .fillna(0)
            .sum()
        )

    def calculate_average_shipment(self, Schedule_df):
        avg = (
            Schedule_df["Shipment_qty"]
            .dropna()
            .mean()
        )

        return 0 if pd.isna(avg) else avg

    def detect_missed_shipments(self, Schedule_df):
        return (
            Schedule_df["Shipment_qty"]
            .isna()
            .sum()
        )

    def calculate_fill_rate(self, Schedule_df):

        total_shipments = len(Schedule_df)

        completed_shipments = (
            Schedule_df["Shipment_qty"]
            .notna()
            .sum()
        )

        if total_shipments == 0:
            return 0

        return (completed_shipments / total_shipments) * 100

    def calculate_supplier_reliability(self, Schedule_df):
        total_shipments = len(Schedule_df)
        successful_shipments = (
            Schedule_df["Shipment_qty"]
            .notna()
            .sum()
        )

        if total_shipments == 0:
            return 0

        return (successful_shipments / total_shipments) * 100

    def identify_single_source_risk(self, supplier_name):

        target = self._normalize(supplier_name)

        names = (
            self.Info_df["Suppplier_name"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        supplier_rows = self.Info_df[
            names.str.contains(re.escape(target), na=False)
        ]

        if supplier_rows.empty:
            return True

        multi_supplier_tanks = (
            supplier_rows["Suppplier_name"]
            .astype(str)
            .str.contains(",")
            .sum()
        )

        return multi_supplier_tanks == 0

    def calculate_supplier_risk_level(self, reliability_score):

        if reliability_score < 80:
            return "CRITICAL"

        elif reliability_score < 90:
            return "HIGH"

        elif reliability_score < 95:
            return "MEDIUM"

        return "LOW"

    def extract_supplier(self, question: str):
        """
        Free-text fallback ONLY - used when run(question) has no
        other way to resolve a supplier. Excludes common words that
        follow "supplier" in ordinary phrasing (details, info,
        reliability, ...) via a negative lookahead, so "Tank 1
        supplier details" does not extract "Supplier details".

        Prefer run_for_supplier(supplier_name) wherever the caller
        already has a clean name - that path skips this regex
        entirely and can't be fooled by phrasing like this.
        """

        match = re.search(
            rf"supplier\s+(?!(?:{SUPPLIER_NAME_STOPWORDS})\b)([A-Za-z0-9][A-Za-z0-9\s]*?)(?:[.?!]|$)",
            question,
            re.IGNORECASE
        )

        if match:
            return f"Supplier {match.group(1).strip()}"

        return None

    def generate_recommendation(self, risk_level, missed_shipments):

        if risk_level == "CRITICAL":
            return "Immediately activate backup suppliers."

        elif risk_level == "HIGH":
            return "Investigate supplier performance and increase monitoring."

        elif missed_shipments > 0:
            return "Review missed deliveries and confirm future schedules."

        return "Supplier performing within expected range."

    @staticmethod
    def can_handle(query: str):

        q = query.lower()

        keywords = [
            "supplier",
            "shipment",
            "delivery",
            "vendor",
            "transport",
            "dispatch",
            "site"
        ]

        return any(k in q for k in keywords)

    def run_for_supplier(self, supplier_name: str) -> SupplierResult:
        """
        Runs the full supplier analysis pipeline for an ALREADY-KNOWN
        supplier name - no regex, no re-parsing a sentence. Use this
        whenever the caller already has a clean name (from extracted
        state, a structured tool arg, or a resolved tank->supplier
        lookup) instead of routing back through run(question), which
        is what previously caused garbled names like "Supplier
        information for Supplier details" when a synthetic sentence
        got re-parsed a second time.
        """

        tanks_served = self.get_supplier_count(supplier_name)
        supplier_df = self.get_supplier_schedule(supplier_name)

        if supplier_df is None:

            if tanks_served > 0:
                raise ValueError(
                    f"'{supplier_name}' is assigned to {tanks_served} "
                    "tank(s) but has no shipment records in the "
                    "schedule yet."
                )

            raise ValueError(
                f"Supplier '{supplier_name}' was not found in supplier records."
            )

        total_shipments = len(supplier_df)
        total_qty = self.calculate_total_shipped_qty(supplier_df)
        avg_qty = self.calculate_average_shipment(supplier_df)
        missed_shipments = self.detect_missed_shipments(supplier_df)
        fill_rate = self.calculate_fill_rate(supplier_df)
        reliability = self.calculate_supplier_reliability(supplier_df)
        single_source = self.identify_single_source_risk(supplier_name)
        risk_level = self.calculate_supplier_risk_level(reliability)
        recommendation = self.generate_recommendation(risk_level, missed_shipments)

        return SupplierResult(
            supplier_name=supplier_name,
            tanks_served=tanks_served,
            total_shipments=total_shipments,
            total_shipment_qty=total_qty,
            avg_shipment_qty=avg_qty,
            missed_shipments=missed_shipments,
            fill_rate=fill_rate,
            reliability_score=reliability,
            single_source_dependency=single_source,
            risk_level=risk_level,
            recommendation=recommendation
        )

    def run(self, question: str) -> SupplierResult:
        """
        Free-text entry point - used only by the LLM tool-agent's
        fallback path, when no supplier/tank was already resolved
        upstream. Extracts a supplier name from the question, or
        resolves one via a named tank, then delegates to
        run_for_supplier() - the same pipeline every other call site
        uses.
        """

        print("Running Supplier Agent...")

        supplier_name = self.extract_supplier(question)

        if not supplier_name:

            tank_id = self.extract_tank_id(question)

            if tank_id:

                resolved = self.get_supplier_for_tank(tank_id)

                if resolved is None:
                    raise ValueError(
                        f"{tank_id} does not have a supplier "
                        "assigned in the current data."
                    )

                supplier_name = resolved

            else:
                raise ValueError(
                    "Please specify a supplier or a tank. "
                    "Example: 'Show supplier information for Supplier A' "
                    "or 'Which supplier serves Tank 16?'"
                )

        return self.run_for_supplier(supplier_name)
