from pydantic import BaseModel, Field


class CompanyReport(BaseModel):
    company_name: str = Field(
        description="Название сущности ТОЧНО как в поле Entity payload — без замены на другой бренд"
    )
    sector: str = Field(description="Сектор; «н/д» если нет в данных")
    industry: str = Field(description="Индустрия; «н/д» если нет в данных")
    key_facts: list[str] = Field(
        description="2–4 ключевых факта из профиля, на русском, только подтверждённые данные"
    )
    positive_factors: list[str] = Field(
        description="Позитивные факторы на русском; отраслевые новости — как контекст сегмента, без прямого приписывания бренду, если он не назван в новости"
    )
    negative_factors: list[str] = Field(
        description="Негативные факторы на русском; то же правило для обобщённых рыночных новостей"
    )
    short_term_outlook: str = Field(
        description="Краткосрочный прогноз, 1–3 предложения на русском, вывод из факторов выше"
    )
    data_limitation_note: str | None = Field(
        default=None,
        description="Ограничения на русском; для бренда без профиля — про материнскую группу, не «нет в базах»; null если данных достаточно",
    )

    def to_markdown(self) -> str:
        lines = [
            f"# Аналитический отчёт: {self.company_name}",
            "",
            "## Обзор",
            f"- Сектор: {self.sector}",
            f"- Индустрия: {self.industry}",
            "- Ключевые факты:",
        ]
        for fact in self.key_facts:
            lines.append(f"  - {fact}")

        lines.extend(["", "## Позитивные факторы"])
        if self.positive_factors:
            lines.extend(f"- {item}" for item in self.positive_factors)
        else:
            lines.append(
                "- Явных позитивных сигналов в новостях и профиле не выявлено; "
                "это может указывать на отсутствие недавних позитивных катализаторов в публичном поле."
            )

        lines.extend(["", "## Негативные факторы"])
        if self.negative_factors:
            lines.extend(f"- {item}" for item in self.negative_factors)
        else:
            lines.append(
                "- Явных негативных сигналов в новостях и профиле не выявлено; "
                "это может свидетельствовать об отсутствии острых недавних рисков в доступных источниках."
            )

        lines.extend(["", "## Краткосрочный прогноз", "", self.short_term_outlook])

        lines.extend(["", "## Ограничения данных", ""])
        if self.data_limitation_note:
            lines.append(self.data_limitation_note)
        else:
            lines.append(
                "Предоставленных профиля и новостей достаточно для базового анализа; "
                "существенных ограничений не зафиксировано."
            )

        lines.append("")
        return "\n".join(lines)
