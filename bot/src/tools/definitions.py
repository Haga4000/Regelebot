TOOLS_DEFINITIONS = [
    {
        "name": "movie_search",
        "description": (
            "Recherche un film par son titre et retourne ses informations completes "
            "(synopsis, casting, note, plateformes de streaming)"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Le titre du film a rechercher",
                },
                "year": {
                    "type": "integer",
                    "description": "L'annee de sortie (optionnel, pour desambiguiser)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_recommendations",
        "description": (
            "Obtient des recommandations de films personnalisees basees sur les gouts du club"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rec_type": {
                    "type": "string",
                    "enum": ["similar", "genre", "mood"],
                    "description": (
                        "Type de recommandation : similar (films similaires), "
                        "genre (par genre), mood (par ambiance)"
                    ),
                },
                "reference": {
                    "type": "string",
                    "description": "Titre du film de reference (requis si rec_type='similar')",
                },
                "genre": {
                    "type": "string",
                    "description": (
                        "Genre souhaite : thriller, comedie, drame, horreur, sf, romance, action, etc."
                    ),
                },
                "mood": {
                    "type": "string",
                    "description": (
                        "Ambiance souhaitee : feel-good, intense, cerebral, leger, sombre, etc."
                    ),
                },
            },
            "required": ["rec_type"],
        },
    },
    {
        "name": "get_club_history",
        "description": "Recupere la liste des films vus par le club avec leurs dates et notes moyennes",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Nombre de films a retourner (defaut: 10)",
                },
            },
        },
    },
    {
        "name": "get_club_stats",
        "description": (
            "Recupere les statistiques completes du club : "
            "nombre de films, note moyenne, genres preferes, top films"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mark_as_watched",
        "description": "Marque un film comme vu par le club a la date du jour",
        "parameters": {
            "type": "object",
            "properties": {
                "movie_title": {
                    "type": "string",
                    "description": "Titre du film a marquer comme vu",
                },
            },
            "required": ["movie_title"],
        },
    },
    {
        "name": "rate_movie",
        "description": "Enregistre la note d'un membre pour un film vu",
        "parameters": {
            "type": "object",
            "properties": {
                "movie_title": {
                    "type": "string",
                    "description": "Titre du film a noter",
                },
                "score": {
                    "type": "integer",
                    "description": "Note de 1 a 5",
                },
                "member_name": {
                    "type": "string",
                    "description": "Nom du membre qui note",
                },
            },
            "required": ["movie_title", "score", "member_name"],
        },
    },
    {
        "name": "create_poll",
        "description": (
            "Cree un sondage pour que les membres du club votent "
            "(choix du prochain film, date de seance, etc.)"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "La question du sondage",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Les options de vote (2 a 10)",
                },
                "member_name": {
                    "type": "string",
                    "description": "Nom du membre qui cree le sondage",
                },
            },
            "required": ["question", "options", "member_name"],
        },
    },
    {
        "name": "vote_on_poll",
        "description": "Enregistre le vote d'un membre sur un sondage en cours",
        "parameters": {
            "type": "object",
            "properties": {
                "poll_id": {
                    "type": "string",
                    "description": "ID du sondage (optionnel, utilise le dernier sondage si absent)",
                },
                "option_id": {
                    "type": "string",
                    "description": "Numero de l'option choisie (ex: '1', '2', '3')",
                },
                "member_name": {
                    "type": "string",
                    "description": "Nom du membre qui vote",
                },
            },
            "required": ["option_id", "member_name"],
        },
    },
    {
        "name": "get_poll_results",
        "description": "Affiche les resultats du sondage en cours ou d'un sondage specifique",
        "parameters": {
            "type": "object",
            "properties": {
                "poll_id": {
                    "type": "string",
                    "description": "ID du sondage (optionnel, utilise le dernier sondage si absent)",
                },
            },
        },
    },
    {
        "name": "close_poll",
        "description": "Cloture un sondage et affiche les resultats finaux",
        "parameters": {
            "type": "object",
            "properties": {
                "poll_id": {
                    "type": "string",
                    "description": "ID du sondage a cloturer (optionnel, utilise le dernier si absent)",
                },
            },
        },
    },
]
