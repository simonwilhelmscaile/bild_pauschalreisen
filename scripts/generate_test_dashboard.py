"""Generate a test dashboard HTML with comprehensive mock data to verify the UI overhaul."""
import json
import os

MOCK_DATA = {
    "period": {
        "start": "2026-02-16",
        "end": "2026-02-22",
        "week_number": 8
    },
    "generated_at": "2026-02-22T10:30:00Z",
    "available_weeks": [
        {"week_start": "2026-02-16", "week_end": "2026-02-22"},
        {"week_start": "2026-02-09", "week_end": "2026-02-15"},
        {"week_start": "2026-02-02", "week_end": "2026-02-08"},
        {"week_start": "2026-01-26", "week_end": "2026-02-01"}
    ],
    "executive_summary": {
        "total_mentions": 847,
        "overall_sentiment": {"positive": 186, "neutral": 458, "negative": 203},
        "overall_sentiment_pct": {"positive": 22, "neutral": 54, "negative": 24},
        "key_insight": "Steigende Diskussionen über Messgenauigkeit bei Blutdruckmessgeräten",
        "top_category": "blood_pressure",
        "top_category_count": 412,
        "negative_pct": 24,
        "competitor_mention_count": 156,
        "device_questions_count": 89
    },
    "wow_metrics": {
        "available": True,
        "mentions_delta": 47,
        "mentions_change": "+47",
        "positive_pct_change": 3,
        "negative_pct_change": -2,
        "competitor_change": 12
    },
    "executive_dashboard": {
        "top_3_insights": [
            {
                "title": "Messgenauigkeit dominiert Diskussionen",
                "description": "42% aller Blutdruck-Beiträge thematisieren Messgenauigkeit — Nutzer vergleichen aktiv Beurer BM 27 mit Omron M500.",
                "action": "Vergleichstest-Content erstellen",
                "tab": "journey"
            },
            {
                "title": "TENS-Nachfrage bei Menstruation steigt",
                "description": "28% mehr Beiträge zu Menstruationsschmerzen und TENS-Therapie. Beurer EM 50 wird häufig empfohlen.",
                "action": "Testimonial-Kampagne starten",
                "tab": "insights"
            },
            {
                "title": "Omron-Nutzer klagen über App-Probleme",
                "description": "Omron Connect App erhält negative Reviews — Chance für Beurer HealthManager Positionierung.",
                "action": "App-Vergleich erstellen",
                "tab": "competitors"
            }
        ]
    },
    "key_actions": [
        {
            "action": "Blutdruck-Vergleichstest BM 27 vs. Omron M500 veröffentlichen",
            "topic": "Messgenauigkeit",
            "priority": "urgent",
            "responsible": "Content-Team",
            "deadline": "KW 9",
            "source": "gutefrage",
            "source_url": "https://www.gutefrage.net/frage/blutdruckmessgeraet-genau"
        },
        {
            "action": "TENS-Ratgeber für Menstruationsschmerzen erstellen",
            "topic": "Menstruation & TENS",
            "priority": "high",
            "responsible": "Marketing",
            "deadline": "KW 10"
        },
        {
            "action": "App-Connectivity FAQ erweitern",
            "topic": "Bluetooth-Probleme",
            "priority": "high",
            "responsible": "Support-Team"
        }
    ],
    "alerts": {
        "critical": [
            {
                "title": "Häufige Fehlanzeigen beim BM 58",
                "topic_summary": "Nutzer berichten von stark schwankenden Messwerten beim BM 58",
                "problem_description": "Mehrere Nutzer in Gesundheitsforen berichten von Abweichungen von 20+ mmHg zwischen aufeinanderfolgenden Messungen.",
                "source": "diabetes-forum.de",
                "url": "https://diabetes-forum.de/thread/12345",
                "product": "Beurer BM 58",
                "relevance_score": 0.95,
                "category": "blood_pressure",
                "emotion": "frustration",
                "intent": "troubleshooting",
                "recommendation": "Qualitätssicherung kontaktieren, FAQ zu korrekter Manschettenanlage erstellen"
            },
            {
                "title": "Sicherheitsbedenken TENS bei Schwangerschaft",
                "topic_summary": "Schwangere fragen nach TENS-Sicherheit",
                "problem_description": "Verunsicherung in Foren über TENS-Anwendung während der Schwangerschaft.",
                "source": "gutefrage",
                "url": "https://gutefrage.net/frage/tens-schwangerschaft",
                "category": "pain_tens",
                "emotion": "anxiety",
                "intent": "general_question",
                "recommendation": "Ärztliche Hinweise prominent in Produktbeschreibungen platzieren"
            }
        ],
        "monitor": [
            {
                "title": "Bluetooth-Verbindungsprobleme häufen sich",
                "topic_summary": "Beurer HealthManager App verliert Bluetooth-Verbindung",
                "context": "5 neue Berichte diese Woche über Verbindungsabbrüche nach App-Update.",
                "source": "reddit",
                "url": "https://reddit.com/r/bloodpressure/abc",
                "device_relevance_score": 0.88,
                "category": "blood_pressure",
                "emotion": "frustration",
                "intent": "troubleshooting"
            },
            {
                "title": "Elektrodenqualität bei EM 49",
                "topic_summary": "Elektroden lösen sich nach wenigen Anwendungen",
                "context": "Nutzer berichten, dass Klebeelektroden nach 3-4 Anwendungen nicht mehr haften.",
                "source": "amazon",
                "url": "https://amazon.de/review/xyz",
                "category": "pain_tens",
                "emotion": "frustration",
                "intent": "complaint"
            }
        ],
        "opportunity": [
            {
                "title": "Großes Interesse an Schlaftracking mit Blutdruck",
                "topic_summary": "Nutzer wünschen sich Blutdruckmessung im Schlaf",
                "opportunity_description": "Mehrere Threads diskutieren nächtliche Blutdruckmessung — Beurer könnte mit BM-Serie + Schlaftracking-Feature punkten.",
                "source": "reddit",
                "url": "https://reddit.com/r/hypertension/def",
                "category": "blood_pressure",
                "emotion": "hope",
                "intent": "purchase_question",
                "recommendation": "Content zu automatischen Messintervallen erstellen"
            },
            {
                "title": "Infrarot-Lampe gegen Winterdepression",
                "topic_summary": "Nutzer suchen Lichttherapie gegen Winterblues",
                "opportunity_description": "Steigende Nachfrage nach Infrarot-Wärmelampen für Wohlbefinden im Winter.",
                "source": "gutefrage",
                "url": "https://gutefrage.net/frage/infrarotlampe-winter",
                "category": "infrarot",
                "emotion": "hope",
                "intent": "purchase_question",
                "recommendation": "Wellness-Positioning für IL-Serie entwickeln"
            }
        ]
    },
    "volume_by_source": {
        "gutefrage": 215, "amazon": 178, "reddit": 142, "diabetes-forum.de": 98,
        "youtube": 87, "onmeda": 65, "tiktok": 42, "instagram": 20
    },
    "volume_by_source_category": {
        "Gesundheitsforen": 378, "E-Commerce": 178, "Social Media": 204, "Video": 87
    },
    "volume_by_source_by_category": {
        "blood_pressure": {"Gesundheitsforen": 198, "E-Commerce": 102, "Social Media": 72, "Video": 40},
        "pain_tens": {"Gesundheitsforen": 112, "E-Commerce": 48, "Social Media": 78, "Video": 32},
        "menstrual": {"Gesundheitsforen": 38, "E-Commerce": 18, "Social Media": 34, "Video": 10},
        "infrarot": {"Gesundheitsforen": 30, "E-Commerce": 10, "Social Media": 20, "Video": 5}
    },
    "volume_by_category": {
        "blood_pressure": 412,
        "pain_tens": 270,
        "menstrual": 100,
        "infrarot": 65
    },
    "sentiment_by_category": {
        "blood_pressure": {"positive": 20, "neutral": 55, "negative": 25, "count": 412},
        "pain_tens": {"positive": 18, "neutral": 48, "negative": 34, "count": 270},
        "menstrual": {"positive": 30, "neutral": 50, "negative": 20, "count": 100},
        "infrarot": {"positive": 35, "neutral": 50, "negative": 15, "count": 65}
    },
    "product_intelligence": {
        "beurer": {
            "BM 27": {"count": 89, "sentiment": {"positive": 28, "neutral": 42, "negative": 19},
                       "mention_types": {"direct": 52, "comparison": 22, "recommendation": 10, "complaint": 5},
                       "top_issues": ["messgenauigkeit"], "top_praise": ["bedienbarkeit", "preis_leistung"]},
            "BM 58": {"count": 67, "sentiment": {"positive": 15, "neutral": 30, "negative": 22},
                       "mention_types": {"direct": 40, "comparison": 15, "recommendation": 5, "complaint": 7},
                       "top_issues": ["app_konnektivitaet", "messgenauigkeit"], "top_praise": ["display_anzeige"]},
            "EM 50": {"count": 54, "sentiment": {"positive": 22, "neutral": 24, "negative": 8},
                       "mention_types": {"direct": 35, "comparison": 8, "recommendation": 8, "complaint": 3},
                       "top_issues": ["manschette_elektroden"], "top_praise": ["schmerzlinderung"]},
            "EM 49": {"count": 41, "sentiment": {"positive": 12, "neutral": 18, "negative": 11},
                       "mention_types": {"direct": 28, "comparison": 6, "recommendation": 4, "complaint": 3},
                       "top_issues": ["manschette_elektroden"], "top_praise": ["preis_leistung"]},
            "IL 50": {"count": 28, "sentiment": {"positive": 14, "neutral": 10, "negative": 4},
                       "mention_types": {"direct": 20, "comparison": 4, "recommendation": 3, "complaint": 1},
                       "top_issues": [], "top_praise": ["schmerzlinderung", "verarbeitung"]}
        },
        "beurer_total": 312,
        "competitors": {
            "Omron M500": {"count": 78, "sentiment": {"positive": 32, "neutral": 28, "negative": 18},
                            "mention_types": {"direct": 45, "comparison": 25, "recommendation": 5, "complaint": 3},
                            "top_issues": ["app_konnektivitaet"], "top_praise": ["messgenauigkeit"]},
            "Omron M400": {"count": 42, "sentiment": {"positive": 18, "neutral": 16, "negative": 8},
                            "mention_types": {"direct": 28, "comparison": 10, "recommendation": 2, "complaint": 2},
                            "top_issues": [], "top_praise": ["bedienbarkeit"]},
            "Sanitas SBM 21": {"count": 18, "sentiment": {"positive": 5, "neutral": 8, "negative": 5},
                                "top_issues": ["messgenauigkeit"], "top_praise": ["preis_leistung"]},
            "AUVON TENS": {"count": 12, "sentiment": {"positive": 4, "neutral": 5, "negative": 3},
                            "top_issues": ["verarbeitung"], "top_praise": ["preis_leistung"]},
            "Medisana BU 510": {"count": 6, "sentiment": {"positive": 2, "neutral": 3, "negative": 1}}
        },
        "competitors_total": 156
    },
    "competitive_intelligence": {
        "context_breakdown": {"Vergleich": 45, "Empfehlung": 28, "Kritik": 18, "Allgemein": 9},
        "competitor_mentions": [
            {"brand": "Omron", "total_mentions": 120, "items": [
                {"title": "Omron M500 vs Beurer BM 27 — welches ist genauer?", "url": "https://gutefrage.net/frage/omron-vs-beurer", "source": "gutefrage", "context": "comparison"},
                {"title": "Omron App funktioniert nicht mehr nach Update", "url": "https://reddit.com/r/test1", "source": "reddit", "context": "complaint"},
                {"title": "Ich empfehle den Omron M400 für Anfänger", "url": "https://gutefrage.net/frage/blutdruck1", "source": "gutefrage", "context": "recommendation"}
            ]},
            {"brand": "Sanitas", "total_mentions": 18, "items": [
                {"title": "Sanitas SBM 21 — taugt das was?", "url": "https://gutefrage.net/frage/sanitas", "source": "gutefrage", "context": "comparison"}
            ]},
            {"brand": "AUVON", "total_mentions": 12, "items": [
                {"title": "AUVON TENS günstiger als Beurer?", "url": "https://amazon.de/review/auvon", "source": "amazon", "context": "comparison"}
            ]}
        ],
        "competitor_weaknesses": [
            {"competitor": "Omron", "issue": "App-Konnektivität häufig gestört", "count": 24,
             "beurer_advantage": "Beurer HealthManager stabiler", "content_idea": "App-Vergleichstest"},
            {"competitor": "Sanitas", "issue": "Manschettenqualität mangelhaft", "count": 8,
             "beurer_advantage": "Hochwertige XL-Manschette", "content_idea": "Manschetten-Ratgeber"},
            {"competitor": "AUVON", "issue": "Keine deutsche Anleitung", "count": 6,
             "beurer_advantage": "Deutsche Qualität mit dt. Support", "content_idea": "Service-Vergleich"}
        ],
        "strategic_summary": "Beurer dominiert im TENS-Segment, Omron bleibt stärker bei Blutdruckmessung. App-Qualität ist der entscheidende Differenzierungsfaktor — hier liegt Beurer's größte Chance.",
        "by_category": {
            "blood_pressure": {
                "label_de": "Blutdruckmessung",
                "context_breakdown": {"Vergleich": 35, "Empfehlung": 20, "Kritik": 12},
                "competitor_weaknesses": [
                    {"competitor": "Omron", "issue": "App-Probleme", "count": 18, "beurer_advantage": "Stabile App", "content_idea": "App-Vergleich"}
                ],
                "competitor_mentions": []
            },
            "pain_tens": {
                "label_de": "Schmerztherapie",
                "context_breakdown": {"Vergleich": 10, "Empfehlung": 8, "Kritik": 6},
                "competitor_weaknesses": [
                    {"competitor": "AUVON", "issue": "Keine deutsche Anleitung", "count": 6, "beurer_advantage": "Dt. Support", "content_idea": "Service-Highlight"}
                ],
                "competitor_mentions": []
            }
        }
    },
    "journey_intelligence": {
        "kpis": {"bridge_rate": 18},
        "narrative": "Die Mehrheit der Nutzer befindet sich in der Lösungssuche-Phase — sie recherchieren aktiv nach dem richtigen Blutdruckmessgerät oder TENS-Gerät. Content, der direkte Vergleiche und Erfahrungsberichte bietet, kann diese Nutzer am effektivsten abholen.",
        "journey_spine": {
            "stages": [
                {
                    "stage": "awareness",
                    "emotion_distribution": {"anxiety": 34, "confusion": 28, "hope": 12},
                    "intent_distribution": {"general_question": 42, "troubleshooting": 18},
                    "pain_breakdown": [
                        {"pain_category": "Rückenschmerzen", "label_de": "Rückenschmerzen", "count": 22},
                        {"pain_category": "Kopfschmerzen", "label_de": "Kopfschmerzen", "count": 15}
                    ],
                    "bridge_to_next": [
                        {"bridge_type": "arzt_empfehlung", "label_de": "Arzt-Empfehlung", "count": 18},
                        {"bridge_type": "online_recherche", "label_de": "Online-Recherche", "count": 12}
                    ],
                    "representative_quotes": [
                        {"text": "Mein Arzt hat gesagt, ich soll meinen Blutdruck regelmäßig messen. Welches Gerät empfehlt ihr?", "source": "gutefrage"}
                    ]
                },
                {
                    "stage": "consideration",
                    "emotion_distribution": {"confusion": 32, "hope": 24, "frustration": 18},
                    "intent_distribution": {"purchase_question": 38, "comparison": 22, "recommendation_request": 16},
                    "pain_breakdown": [
                        {"pain_category": "Bluthochdruck", "label_de": "Bluthochdruck", "count": 35},
                        {"pain_category": "Menstruationsschmerzen", "label_de": "Menstruationsschmerzen", "count": 18}
                    ],
                    "bridge_to_next": [
                        {"bridge_type": "preisvergleich", "label_de": "Preisvergleich", "count": 22},
                        {"bridge_type": "testbericht", "label_de": "Testbericht gelesen", "count": 15}
                    ],
                    "representative_quotes": [
                        {"text": "Hat jemand Erfahrung mit dem Beurer BM 27? Lohnt sich der Aufpreis gegenüber Sanitas?", "source": "gutefrage"}
                    ]
                },
                {
                    "stage": "comparison",
                    "emotion_distribution": {"confusion": 25, "frustration": 20, "satisfaction": 10},
                    "intent_distribution": {"comparison": 45, "purchase_question": 25},
                    "representative_quotes": [
                        {"text": "Beurer BM 27 vs. Omron M500 — wer hat den besseren Vergleich?", "source": "reddit"}
                    ]
                },
                {
                    "stage": "purchase",
                    "emotion_distribution": {"satisfaction": 30, "anxiety": 15, "hope": 20},
                    "intent_distribution": {"purchase_question": 35, "experience_sharing": 20},
                    "representative_quotes": []
                },
                {
                    "stage": "advocacy",
                    "emotion_distribution": {"satisfaction": 42, "frustration": 12, "relief": 18},
                    "intent_distribution": {"experience_sharing": 38, "advocacy": 25, "complaint": 10},
                    "representative_quotes": [
                        {"text": "Beurer BM 27 läuft seit 2 Jahren problemlos. Kann ich nur empfehlen!", "source": "amazon"}
                    ]
                }
            ]
        },
        "qa_threads": [
            {
                "question": "Welches Blutdruckmessgerät ist am genauesten für den Heimgebrauch?",
                "source": "gutefrage", "url": "https://gutefrage.net/frage/blutdruck-genau",
                "category": "blood_pressure", "journey_stage": "comparison",
                "answer_count": 8, "posted_at": "2026-02-18",
                "entities": ["BM 27", "Omron M500"],
                "bridge_types": ["comparison_to_purchase"],
                "answers": [
                    {"content": "Ich nutze den Beurer BM 27 seit einem Jahr und bin sehr zufrieden mit der Genauigkeit.", "author": "Gesundheitsfan92", "is_accepted": True, "votes": 12},
                    {"content": "Omron M500 ist im Test besser, aber deutlich teurer.", "author": "BlutdruckExperte", "votes": 8}
                ],
                "analysis": "Direkte Kaufentscheidungs-Situation. Nutzer vergleicht aktiv Beurer vs. Omron — idealer Moment für Content.",
                "action": "SEO-optimierten Vergleichsartikel BM 27 vs. M500 erstellen."
            },
            {
                "question": "TENS-Gerät gegen Menstruationsschmerzen — hat jemand Erfahrung?",
                "source": "gutefrage", "url": "https://gutefrage.net/frage/tens-menstruation",
                "category": "menstrual", "journey_stage": "consideration",
                "answer_count": 5, "posted_at": "2026-02-19",
                "entities": ["EM 50"],
                "bridge_types": ["awareness_to_consideration"],
                "answers": [
                    {"content": "Der Beurer EM 50 hat mir sehr geholfen! Nach 20 Minuten waren die Schmerzen deutlich besser.", "author": "Lisa_M", "is_accepted": False, "votes": 15},
                    {"content": "Ich nutze meinen TENS seit 3 Monaten bei jeder Periode. Absolute Empfehlung.", "author": "PainFree23", "votes": 9}
                ],
                "analysis": "Hohe Beurer-Relevanz: EM 50 wird positiv erwähnt, Nutzerin teilt Erfolgsgeschichte.",
                "action": "Testimonial für Social Media aufbereiten."
            },
            {
                "question": "Beurer BM 58 zeigt unterschiedliche Werte — defekt?",
                "source": "diabetes-forum.de", "url": "https://diabetes-forum.de/thread/bm58",
                "category": "blood_pressure", "journey_stage": "advocacy",
                "answer_count": 12, "posted_at": "2026-02-17",
                "entities": ["BM 58"],
                "bridge_types": [],
                "answers": [
                    {"content": "Hast du die Manschette richtig angelegt? Das ist der häufigste Fehler.", "author": "Diabetes_Doc", "is_accepted": True, "votes": 20},
                    {"content": "Ich hatte dasselbe Problem, nach Manschettentausch war alles ok.", "author": "BPMonitor", "votes": 6}
                ],
                "analysis": "Kritisches Support-Thema. Nutzer ist frustriert, aber Lösung ist einfach (Manschettenanlage).",
                "action": "Video-Tutorial zur korrekten Manschettenanlage erstellen."
            },
            {
                "question": "Infrarotlampe gegen Nackenschmerzen — welche empfehlt ihr?",
                "source": "gutefrage", "url": "https://gutefrage.net/frage/infrarot-nacken",
                "category": "infrarot", "journey_stage": "consideration",
                "answer_count": 4, "posted_at": "2026-02-20",
                "entities": ["IL 50"],
                "bridge_types": [],
                "answers": [
                    {"content": "Beurer IL 50 ist top! Gute Wärmeverteilung und Timer-Funktion.", "author": "WärmeFreund", "votes": 7}
                ]
            },
            {
                "question": "Erfahrungen mit TENS bei Endometriose?",
                "source": "endometriose-forum",
                "url": "https://endometriose-forum.de/thread/tens",
                "category": "pain_tens", "journey_stage": "consideration",
                "answer_count": 6, "posted_at": "2026-02-16",
                "entities": [],
                "bridge_types": ["awareness_to_consideration"],
                "answers": [
                    {"content": "TENS hat mir bei meiner Endo wirklich geholfen, besonders in Kombination mit Wärme.", "author": "EndoKämpferin", "is_accepted": True, "votes": 18}
                ],
                "analysis": "Starke Community-Empfehlung für TENS bei Endometriose. Beurer nicht namentlich erwähnt — Chance.",
                "action": "Endometriose-spezifischen TENS-Ratgeber mit EM 50/EM 49 Empfehlung erstellen."
            },
            {
                "question": "Welcher Blutdruckmesser hat die beste App?",
                "source": "reddit", "url": "https://reddit.com/r/health/abc",
                "category": "blood_pressure", "journey_stage": "comparison",
                "answer_count": 15, "posted_at": "2026-02-18",
                "entities": ["BM 58", "Omron M500"],
                "bridge_types": ["comparison_to_purchase"],
                "answers": [
                    {"content": "Omron Connect ist leider echt buggy. Beurer HealthManager läuft stabiler bei mir.", "author": "TechHealth", "votes": 22},
                    {"content": "Withings BPM Connect hat die beste App, aber ist auch am teuersten.", "author": "GadgetGuru", "votes": 14}
                ]
            }
        ],
        "bridge_summary": {
            "total_detected": 152,
            "patterns": [
                {"bridge_type": "comparison_to_purchase", "label_de": "Vergleich → Kauf", "label_en": "Comparison → Purchase", "count": 48},
                {"bridge_type": "awareness_to_consideration", "label_de": "Bewusstsein → Recherche", "label_en": "Awareness → Research", "count": 38},
                {"bridge_type": "consideration_to_comparison", "label_de": "Recherche → Vergleich", "label_en": "Research → Comparison", "count": 35},
                {"bridge_type": "purchase_to_advocacy", "label_de": "Kauf → Empfehlung", "label_en": "Purchase → Advocacy", "count": 31}
            ]
        }
    },
    "category_journeys": {
        "all": {
            "label_de": "Alle Kategorien",
            "total_items": 847,
            "funnel": {
                "total": 847,
                "stages": [
                    {"stage": "awareness", "label_de": "Bewusstsein", "count": 186, "percentage": 22},
                    {"stage": "consideration", "label_de": "Lösungssuche", "count": 287, "percentage": 34},
                    {"stage": "comparison", "label_de": "Vergleich", "count": 203, "percentage": 24},
                    {"stage": "purchase", "label_de": "Kaufentscheidung", "count": 102, "percentage": 12},
                    {"stage": "advocacy", "label_de": "Erfahrung & Empfehlung", "count": 69, "percentage": 8}
                ]
            },
            "pain_breakdown": {
                "total": 320,
                "categories": [
                    {"pain_category": "Rückenschmerzen", "label_de": "Rückenschmerzen", "count": 95, "percentage": 30},
                    {"pain_category": "Bluthochdruck", "label_de": "Bluthochdruck", "count": 78, "percentage": 24},
                    {"pain_category": "Menstruationsschmerzen", "label_de": "Menstruationsschmerzen", "count": 55, "percentage": 17},
                    {"pain_category": "Kopfschmerzen", "label_de": "Kopfschmerzen", "count": 42, "percentage": 13},
                    {"pain_category": "Gelenkschmerzen", "label_de": "Gelenkschmerzen", "count": 32, "percentage": 10},
                    {"pain_category": "Nackenschmerzen", "label_de": "Nackenschmerzen", "count": 18, "percentage": 6}
                ],
                "resolved_sonstige": [
                    {"location": "Schulter", "label_de": "Schulterschmerzen", "count": 8},
                    {"location": "Knie", "label_de": "Knieschmerzen", "count": 5}
                ]
            },
            "stages": [
                {
                    "stage": "awareness", "label_de": "Bewusstsein", "count": 186, "percentage": 22,
                    "emotional_state": {"positive": 12, "neutral": 58, "negative": 30},
                    "life_situations": [
                        {"key": "Erstdiagnose Bluthochdruck", "label_de": "Erstdiagnose Bluthochdruck", "count": 45},
                        {"key": "Chronische Schmerzen", "label_de": "Chronische Schmerzen", "count": 38},
                        {"key": "Schwangerschaft", "label_de": "Schwangerschaft", "count": 22}
                    ],
                    "coping_strategies": [
                        {"key": "Arztbesuch", "label_de": "Arztbesuch", "count": 52, "positive_pct": 15},
                        {"key": "Selbstmedikation", "label_de": "Selbstmedikation", "count": 34, "positive_pct": 8}
                    ],
                    "frustrations": [
                        {"key": "Unklarheit über Normalwerte", "label_de": "Unklarheit über Normalwerte", "count": 28,
                         "quote": "Ich weiß nicht mal, ab welchem Wert Bluthochdruck anfängt..."},
                        {"key": "Lange Wartezeiten beim Arzt", "label_de": "Lange Wartezeiten beim Arzt", "count": 18}
                    ],
                    "top_questions": [
                        {"title": "Ab welchem Blutdruckwert muss ich mir Sorgen machen?", "source": "gutefrage"}
                    ],
                    "all_posts": [
                        {"title": "Blutdruck 140/90 — ist das schon gefährlich?", "url": "https://gutefrage.net/frage/1", "source": "gutefrage", "sentiment": "negative", "category": "blood_pressure"},
                        {"title": "Arzt empfiehlt tägliches Blutdruckmessen", "url": "https://diabetes-forum.de/1", "source": "diabetes-forum.de", "sentiment": "neutral", "category": "blood_pressure"},
                        {"title": "Rückenschmerzen seit 3 Monaten — was tun?", "url": "https://gutefrage.net/frage/2", "source": "gutefrage", "sentiment": "negative", "category": "pain_tens"},
                        {"title": "Schwangerschaftsbluthochdruck — Erfahrungen?", "url": "https://gutefrage.net/frage/3", "source": "gutefrage", "sentiment": "negative", "category": "blood_pressure"},
                        {"title": "Erste Migräne mit 30 — normal?", "url": "https://onmeda.de/frage/1", "source": "onmeda", "sentiment": "neutral", "category": "pain_tens"}
                    ]
                },
                {
                    "stage": "consideration", "label_de": "Lösungssuche", "count": 287, "percentage": 34,
                    "emotional_state": {"positive": 18, "neutral": 52, "negative": 30},
                    "life_situations": [
                        {"key": "Selbstmanagement", "label_de": "Selbstmanagement", "count": 68},
                        {"key": "Periodenschmerzen", "label_de": "Periodenschmerzen", "count": 42}
                    ],
                    "coping_strategies": [
                        {"key": "Online-Recherche", "label_de": "Online-Recherche", "count": 85, "positive_pct": 22},
                        {"key": "TENS-Therapie", "label_de": "TENS-Therapie", "count": 48, "positive_pct": 35}
                    ],
                    "frustrations": [
                        {"key": "Zu viele Optionen", "label_de": "Zu viele Optionen", "count": 42},
                        {"key": "Widersprüchliche Testberichte", "label_de": "Widersprüchliche Testberichte", "count": 28}
                    ],
                    "all_posts": []
                },
                {
                    "stage": "comparison", "label_de": "Vergleich", "count": 203, "percentage": 24,
                    "emotional_state": {"positive": 20, "neutral": 55, "negative": 25},
                    "life_situations": [
                        {"key": "Preisbewusst", "label_de": "Preisbewusst", "count": 52}
                    ],
                    "coping_strategies": [
                        {"key": "Testberichte lesen", "label_de": "Testberichte lesen", "count": 65, "positive_pct": 28}
                    ],
                    "frustrations": [
                        {"key": "Unklare Unterschiede zwischen Modellen", "label_de": "Unklare Unterschiede zwischen Modellen", "count": 35}
                    ],
                    "all_posts": []
                },
                {
                    "stage": "purchase", "label_de": "Kaufentscheidung", "count": 102, "percentage": 12,
                    "emotional_state": {"positive": 35, "neutral": 45, "negative": 20},
                    "life_situations": [],
                    "coping_strategies": [],
                    "frustrations": [
                        {"key": "Preis-Unsicherheit", "label_de": "Preis-Unsicherheit", "count": 18}
                    ],
                    "all_posts": []
                },
                {
                    "stage": "advocacy", "label_de": "Erfahrung & Empfehlung", "count": 69, "percentage": 8,
                    "emotional_state": {"positive": 48, "neutral": 35, "negative": 17},
                    "life_situations": [],
                    "coping_strategies": [],
                    "frustrations": [],
                    "all_posts": []
                }
            ]
        },
        "blood_pressure": {
            "label_de": "Blutdruckmessung",
            "total_items": 412,
            "funnel": {
                "total": 412,
                "stages": [
                    {"stage": "awareness", "label_de": "Bewusstsein", "count": 82, "percentage": 20},
                    {"stage": "consideration", "label_de": "Lösungssuche", "count": 148, "percentage": 36},
                    {"stage": "comparison", "label_de": "Vergleich", "count": 107, "percentage": 26},
                    {"stage": "purchase", "label_de": "Kaufentscheidung", "count": 45, "percentage": 11},
                    {"stage": "advocacy", "label_de": "Erfahrung & Empfehlung", "count": 30, "percentage": 7}
                ]
            },
            "pain_breakdown": {"total": 0, "categories": []},
            "stages": []
        },
        "pain_tens": {
            "label_de": "Schmerztherapie (TENS/EMS)",
            "total_items": 270,
            "funnel": {
                "total": 270,
                "stages": [
                    {"stage": "awareness", "label_de": "Bewusstsein", "count": 68, "percentage": 25},
                    {"stage": "consideration", "label_de": "Lösungssuche", "count": 89, "percentage": 33},
                    {"stage": "comparison", "label_de": "Vergleich", "count": 62, "percentage": 23},
                    {"stage": "purchase", "label_de": "Kaufentscheidung", "count": 30, "percentage": 11},
                    {"stage": "advocacy", "label_de": "Erfahrung & Empfehlung", "count": 21, "percentage": 8}
                ]
            },
            "pain_breakdown": {
                "total": 220,
                "categories": [
                    {"pain_category": "Rückenschmerzen", "label_de": "Rückenschmerzen", "count": 78, "percentage": 35},
                    {"pain_category": "Nackenschmerzen", "label_de": "Nackenschmerzen", "count": 42, "percentage": 19},
                    {"pain_category": "Gelenkschmerzen", "label_de": "Gelenkschmerzen", "count": 35, "percentage": 16}
                ]
            },
            "stages": []
        }
    },
    "category_deep_insights": {
        "all": {
            "label_de": "Alle",
            "total_items": 847,
            "coping_analysis": {
                "strategies": [
                    {
                        "key": "tens_therapy", "label_de": "TENS-Therapie", "count": 128,
                        "effectiveness_pct": 35,
                        "sentiment": {"positive": 45, "neutral": 52, "negative": 31, "positive_pct": 35, "neutral_pct": 41, "negative_pct": 24},
                        "category_distribution": [{"label_de": "Schmerztherapie", "count": 95}, {"label_de": "Menstruation", "count": 33}],
                        "journey_stages": [{"label_de": "Lösungssuche", "count": 48}, {"label_de": "Erfahrung", "count": 35}],
                        "pain_profile": [
                            {"label_de": "Rückenschmerzen", "count": 42},
                            {"label_de": "Menstruationsschmerzen", "count": 33},
                            {"label_de": "Nackenschmerzen", "count": 18}
                        ],
                        "frustrations": [
                            {"label_de": "Elektroden halten nicht", "count": 15},
                            {"label_de": "Keine sofortige Wirkung", "count": 12}
                        ],
                        "quotes": [
                            {"text": "TENS hat mir bei meinen chronischen Rückenschmerzen wirklich geholfen!", "source": "gutefrage", "url": "https://gutefrage.net/frage/tens-ruecken"},
                            {"text": "Nach 3 Wochen regelmäßiger Anwendung merke ich eine deutliche Besserung.", "source": "reddit"}
                        ],
                        "content_angle": "Langzeit-Erfahrungsberichte von TENS-Nutzern sammeln und als Ratgeber aufbereiten",
                        "all_posts": [
                            {"title": "TENS gegen Rückenschmerzen — meine Erfahrung nach 6 Monaten", "url": "https://gutefrage.net/frage/tens1", "source": "gutefrage", "sentiment": "positive", "category": "pain_tens"},
                            {"title": "Hilft TENS wirklich bei chronischen Schmerzen?", "url": "https://reddit.com/r/pain/1", "source": "reddit", "sentiment": "neutral", "category": "pain_tens"}
                        ]
                    },
                    {
                        "key": "medication", "label_de": "Medikamente", "count": 95,
                        "effectiveness_pct": 22,
                        "sentiment": {"positive": 21, "neutral": 42, "negative": 32, "positive_pct": 22, "neutral_pct": 44, "negative_pct": 34},
                        "category_distribution": [{"label_de": "Schmerztherapie", "count": 62}, {"label_de": "Blutdruck", "count": 33}],
                        "pain_profile": [
                            {"label_de": "Kopfschmerzen", "count": 28},
                            {"label_de": "Rückenschmerzen", "count": 22}
                        ],
                        "frustrations": [
                            {"label_de": "Nebenwirkungen", "count": 18},
                            {"label_de": "Keine langfristige Lösung", "count": 12}
                        ],
                        "quotes": [],
                        "all_posts": []
                    },
                    {
                        "key": "exercise", "label_de": "Bewegung/Sport", "count": 72,
                        "effectiveness_pct": 42,
                        "sentiment": {"positive": 30, "neutral": 28, "negative": 14, "positive_pct": 42, "neutral_pct": 39, "negative_pct": 19},
                        "category_distribution": [{"label_de": "Blutdruck", "count": 45}, {"label_de": "Schmerztherapie", "count": 27}],
                        "pain_profile": [],
                        "frustrations": [],
                        "quotes": [],
                        "all_posts": []
                    }
                ]
            },
            "frustration_map": {
                "frustrations": [
                    {"label_de": "Ungenaue Messwerte", "count": 45, "top_journey_stage": "Erfahrung", "content_solution": "Messanleitung-Video"},
                    {"label_de": "App-Verbindungsprobleme", "count": 32, "top_journey_stage": "Erfahrung", "content_solution": "Troubleshooting-Guide"},
                    {"label_de": "Elektroden-Qualität", "count": 28, "top_journey_stage": "Erfahrung", "content_solution": "Pflege-Ratgeber"},
                    {"label_de": "Zu viele Modelle", "count": 24, "top_journey_stage": "Vergleich", "content_solution": "Produktvergleich-Tool"},
                    {"label_de": "Hoher Preis", "count": 18, "top_journey_stage": "Kaufentscheidung", "content_solution": "Preis-Leistungs-Vergleich"}
                ]
            },
            "pain_sub": {
                "total_items": 220,
                "by_location": [
                    {"label_de": "Rücken", "count": 78},
                    {"label_de": "Nacken", "count": 42},
                    {"label_de": "Gelenke", "count": 35},
                    {"label_de": "Kopf", "count": 28},
                    {"label_de": "Unterleib", "count": 22},
                    {"label_de": "Schulter", "count": 15}
                ]
            },
            "bp_sub": {
                "total_items": 180,
                "by_concern": [
                    {"label_de": "Messgenauigkeit", "count": 65},
                    {"label_de": "Hohe Werte", "count": 48},
                    {"label_de": "Schwankende Werte", "count": 35},
                    {"label_de": "Weißkittel-Hypertonie", "count": 18},
                    {"label_de": "Medikamenten-Wirkung", "count": 14}
                ]
            },
            "life_situations": {
                "personas": [
                    {
                        "key": "senior_bp", "label_de": "Senioren mit Bluthochdruck", "count": 120,
                        "top_coping": "Tägliche Messung", "top_frustration": "Technik-Unsicherheit",
                        "top_bridge_moment": "Arzt-Empfehlung", "top_content_opportunity": "Einfache Bedienungsanleitung",
                        "all_posts": [
                            {"title": "Blutdruckmesser für meine 78-jährige Mutter", "url": "https://gutefrage.net/frage/senior1", "source": "gutefrage", "sentiment": "neutral", "category": "blood_pressure"},
                            {"title": "Großes Display wichtig für Senioren", "url": "https://amazon.de/review/senior1", "source": "amazon", "sentiment": "positive", "category": "blood_pressure"}
                        ]
                    },
                    {
                        "key": "young_pain", "label_de": "Junge Erwachsene mit Schmerzen", "count": 85,
                        "top_coping": "TENS-Therapie", "top_frustration": "Hohe Kosten",
                        "top_bridge_moment": "Online-Recherche", "top_content_opportunity": "Starter-Guide TENS",
                        "all_posts": []
                    },
                    {
                        "key": "menstrual_sufferers", "label_de": "Frauen mit Periodenschmerzen", "count": 65,
                        "top_coping": "Wärme + TENS", "top_frustration": "Keine dauerhafte Lösung",
                        "top_bridge_moment": "Empfehlung von Freundin", "top_content_opportunity": "Period Pain Guide",
                        "all_posts": []
                    }
                ]
            },
            "aspect_analysis": {
                "total_items_with_aspects": 420,
                "aspects": [
                    {"aspect": "messgenauigkeit", "label_de": "Messgenauigkeit", "total_mentions": 145,
                     "positive_pct": 35, "neutral_pct": 30, "negative_pct": 35, "avg_intensity": 3.8,
                     "mentions": [
                         {"text": "Messgenauigkeit ist top, stimmt mit Arzt-Werten überein", "sentiment": "positive", "source": "amazon", "url": "https://amazon.de/1"},
                         {"text": "Werte schwanken bei jeder Messung um 15 mmHg", "sentiment": "negative", "source": "gutefrage", "url": "https://gutefrage.net/1"},
                         {"text": "Für den Preis okay, aber nicht klinisch genau", "sentiment": "neutral", "source": "reddit", "url": "https://reddit.com/1"}
                     ]},
                    {"aspect": "bedienbarkeit", "label_de": "Bedienbarkeit", "total_mentions": 112,
                     "positive_pct": 55, "neutral_pct": 30, "negative_pct": 15, "avg_intensity": 2.5,
                     "mentions": []},
                    {"aspect": "app_konnektivitaet", "label_de": "App/Konnektivität", "total_mentions": 98,
                     "positive_pct": 20, "neutral_pct": 25, "negative_pct": 55, "avg_intensity": 4.1,
                     "mentions": [
                         {"text": "Bluetooth-Verbindung bricht ständig ab", "sentiment": "negative", "source": "reddit", "url": "https://reddit.com/2"},
                         {"text": "App synchronisiert nicht mehr seit dem Update", "sentiment": "negative", "source": "amazon", "url": "https://amazon.de/2"}
                     ]},
                    {"aspect": "preis_leistung", "label_de": "Preis-Leistung", "total_mentions": 85,
                     "positive_pct": 48, "neutral_pct": 32, "negative_pct": 20, "avg_intensity": 2.8,
                     "mentions": []},
                    {"aspect": "schmerzlinderung", "label_de": "Schmerzlinderung", "total_mentions": 72,
                     "positive_pct": 52, "neutral_pct": 28, "negative_pct": 20, "avg_intensity": 3.4,
                     "mentions": []},
                    {"aspect": "manschette_elektroden", "label_de": "Manschette/Elektroden", "total_mentions": 58,
                     "positive_pct": 25, "neutral_pct": 30, "negative_pct": 45, "avg_intensity": 3.6,
                     "mentions": []}
                ]
            },
            "medication_breakdown": {
                "by_class": {
                    "Schmerzmittel": {
                        "total": 48,
                        "medications": [
                            {"medication": "Ibuprofen", "count": 22},
                            {"medication": "Paracetamol", "count": 15},
                            {"medication": "Aspirin", "count": 11}
                        ]
                    },
                    "Blutdrucksenker": {
                        "total": 35,
                        "medications": [
                            {"medication": "Ramipril", "count": 15},
                            {"medication": "Metoprolol", "count": 12},
                            {"medication": "Amlodipin", "count": 8}
                        ]
                    }
                }
            }
        },
        "blood_pressure": {
            "label_de": "Blutdruckmessung",
            "total_items": 412,
            "coping_analysis": {"strategies": []},
            "frustration_map": {"frustrations": []},
            "pain_sub": {"total_items": 0, "by_location": []},
            "bp_sub": {
                "total_items": 180,
                "by_concern": [
                    {"label_de": "Messgenauigkeit", "count": 65},
                    {"label_de": "Hohe Werte", "count": 48},
                    {"label_de": "Schwankende Werte", "count": 35}
                ]
            },
            "life_situations": {"personas": []},
            "aspect_analysis": {"total_items_with_aspects": 0, "aspects": []}
        },
        "pain_tens": {
            "label_de": "Schmerztherapie",
            "total_items": 270,
            "coping_analysis": {"strategies": []},
            "frustration_map": {"frustrations": []},
            "pain_sub": {
                "total_items": 220,
                "by_location": [
                    {"label_de": "Rücken", "count": 78},
                    {"label_de": "Nacken", "count": 42}
                ]
            },
            "bp_sub": {"total_items": 0, "by_concern": []},
            "life_situations": {"personas": []},
            "aspect_analysis": {"total_items_with_aspects": 0, "aspects": []}
        },
        "menstrual": {
            "label_de": "Menstruation",
            "total_items": 100,
            "coping_analysis": {"strategies": []},
            "frustration_map": {"frustrations": []},
            "pain_sub": {"total_items": 0, "by_location": []},
            "bp_sub": {"total_items": 0, "by_concern": []},
            "life_situations": {"personas": []},
            "aspect_analysis": {"total_items_with_aspects": 0, "aspects": []}
        }
    },
    "content_opportunities": [
        {
            "topic": "Blutdruckmessgerät Vergleich 2026",
            "suggested_title": "Beurer BM 27 vs. Omron M500: Welches Blutdruckmessgerät ist besser?",
            "category": "blood_pressure",
            "gap_score": 8.5,
            "search_intent": "comparison",
            "keywords": ["blutdruckmessgerät vergleich", "beurer vs omron", "bm 27 test"],
            "content_brief": "Detaillierter Vergleichstest mit Messgenauigkeit, App-Funktionen, Preis-Leistung. Fokus auf Alleinstellungsmerkmale des BM 27.",
            "url": "https://gutefrage.net/frage/blutdruck-vergleich"
        },
        {
            "topic": "TENS bei Menstruationsschmerzen",
            "suggested_title": "TENS gegen Periodenschmerzen: So funktioniert die natürliche Schmerzlinderung",
            "category": "menstrual",
            "gap_score": 7.8,
            "search_intent": "informational",
            "keywords": ["tens menstruation", "periodenschmerzen lindern", "tens gerät periode"],
            "content_brief": "Wissenschaftlich fundierter Ratgeber zu TENS bei Menstruationsschmerzen mit Beurer EM 50 Empfehlung.",
            "url": "https://gutefrage.net/frage/tens-periode"
        },
        {
            "topic": "Blutdruck richtig messen Anleitung",
            "suggested_title": "Blutdruck richtig messen: 7 Fehler, die Ihre Werte verfälschen",
            "category": "blood_pressure",
            "gap_score": 7.2,
            "search_intent": "informational",
            "keywords": ["blutdruck richtig messen", "blutdruck messfehler", "manschette anlegen"],
            "content_brief": "Schritt-für-Schritt-Anleitung mit häufigen Fehlern und deren Auswirkung auf Messwerte.",
            "url": "https://gutefrage.net/frage/blutdruck-messen"
        },
        {
            "topic": "TENS Rückenschmerzen Erfahrung",
            "suggested_title": "TENS gegen Rückenschmerzen: Erfahrungsberichte und Tipps zur Anwendung",
            "category": "pain_tens",
            "gap_score": 6.5,
            "search_intent": "informational",
            "keywords": ["tens rückenschmerzen", "tens gerät erfahrung", "tens anwendung rücken"],
            "content_brief": "Erfahrungsbericht-Sammlung mit Anwendungstipps für verschiedene Schmerzarten.",
            "url": "https://reddit.com/r/pain/tens"
        },
        {
            "topic": "Infrarotlampe Anwendungsgebiete",
            "suggested_title": "Infrarotlampe: 5 Anwendungsgebiete, die Sie kennen sollten",
            "category": "infrarot",
            "gap_score": 5.2,
            "search_intent": "informational",
            "keywords": ["infrarotlampe anwendung", "rotlicht therapie", "infrarot gesundheit"],
            "content_brief": "Überblick über Anwendungsbereiche von Infrarotlampen mit Produktempfehlungen.",
            "url": "https://gutefrage.net/frage/infrarot"
        },
        {
            "topic": "Blutdruckmessgerät App Vergleich",
            "suggested_title": "Blutdruck-Apps im Test: Beurer HealthManager vs. Omron Connect",
            "category": "blood_pressure",
            "gap_score": 4.8,
            "search_intent": "comparison",
            "keywords": ["blutdruck app", "healthmanager app", "omron connect app"],
            "content_brief": "App-Funktionsvergleich mit Screenshots und Nutzerbewertungen."
        }
    ]
}


def main():
    template_path = os.path.join(os.path.dirname(__file__), 'styles', 'dashboard_template.html')
    output_path = os.path.join(os.path.dirname(__file__), 'test_ui_overhaul.html')

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    data_json = json.dumps(MOCK_DATA, ensure_ascii=False, default=str)
    html = template.replace('__DASHBOARD_DATA__', data_json)
    html = html.replace('__DEFAULT_LANG__', 'de')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Test dashboard generated: {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.0f} KB")


if __name__ == '__main__':
    main()
