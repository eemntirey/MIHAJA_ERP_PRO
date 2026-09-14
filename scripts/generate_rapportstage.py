# -*- coding: utf-8 -*-
"""
Génère rapportstage.docx à la racine du projet MIHAJA_ERP_PRO.
Structure identique au rapport modèle (Boky Andrea.pdf) :
page de garde, CV, avant-propos, dédicaces, remerciements, listes des
figures/tableaux/abréviations, table de matière, introduction, 3 parties
(presentation, analyse & conception, réalisation), conclusion,
bibliographie, annexe, résumé/abstract.
Les champs personnels / entreprise d'accueil sont laissés VIDES.
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = r"c:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO"
OUT = ROOT + r"\rapportstage.docx"

doc = Document()

# ---------------------------------------------------------------- styles
def _set_style_font(style, name='Times New Roman', size=12, bold=False):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:ascii'), name)
    rfonts.set(qn('w:hAnsi'), name)
    rfonts.set(qn('w:cs'), name)

_set_style_font(doc.styles['Normal'], size=12)
doc.styles['Normal'].paragraph_format.space_after = Pt(6)
for lvl, size in [('Heading 1', 15), ('Heading 2', 14), ('Heading 3', 12.5),
                  ('Heading 4', 12)]:
    _set_style_font(doc.styles[lvl], size=size, bold=True)

def p(text='', align=None, bold=False, italic=False, size=None, space_after=None):
    par = doc.add_paragraph()
    if align is not None:
        par.alignment = align
    if space_after is not None:
        par.paragraph_format.space_after = Pt(space_after)
    if text:
        run = par.add_run(text)
        run.bold = bold
        run.italic = italic
        if size:
            run.font.size = Pt(size)
    return par

def center(text, bold=False, size=None, italic=False):
    return p(text, align=WD_ALIGN_PARAGRAPH.CENTER, bold=bold, size=size,
             italic=italic)

def h(level, text):
    return doc.add_heading(text, level=level)

def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

def caption(text):
    """Légende de figure / tableau (italique, centré, 10 pt)."""
    return p(text, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, size=10)

def figure_placeholder(name):
    """Ligne vide à compléter avec une capture d'écran + légende."""
    p('')
    caption(name)
    p('[Insérer ici la figure / capture d’écran]')

def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    for i, htxt in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ''
        run = cell.paragraphs[0].add_run(htxt)
        run.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    return t

def add_page_number(paragraph):
    run = paragraph.add_run()
    fld1 = OxmlElement('w:fldChar')
    fld1.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = 'PAGE'
    fld2 = OxmlElement('w:fldChar')
    fld2.set(qn('w:fldCharType'), 'end')
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)

footer = doc.sections[0].footer
footer_para = footer.paragraphs[0]
footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_page_number(footer_para)

def add_toc():
    """Champ TOC Word : clic droit > « Mettre à jour les champs »."""
    par = doc.add_paragraph()
    run = par.add_run()
    fld1 = OxmlElement('w:fldChar')
    fld1.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = r'TOC \o "1-3" \h \z \u'
    fld2 = OxmlElement('w:fldChar')
    fld2.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t')
    t.text = ('Table des matières automatique : clic droit puis '
              '« Mettre à jour les champs » pour l’actualiser.')
    fld3 = OxmlElement('w:fldChar')
    fld3.set(qn('w:fldCharType'), 'end')
    for el in (fld1, instr, fld2, t, fld3):
        run._r.append(el)

# ================================================================
# PAGE DE GARDE (identique au modèle — champs personnels laissés vides)
# ================================================================
center('UNIVERSITE DE FIANARANTSOA', bold=True, size=14)
center('ECOLE DE MANAGEMENT ET D’INNOVATION TECHNOLOGIQUE', bold=True, size=13)
center('Mention : INFORMATIQUE', bold=True)
center('Parcours : Développement d’Application Intranet-Internet (D.A.2.I)', bold=True)
center('Rapport de stage en vue de passage en troisième année de formation '
       'licence professionnelle', bold=True)
p('')
p('')
p('')
center('Présenté par : ', bold=True)
center('Enseignants Responsables de mention : ', bold=True)
center('Evaluateur : ', bold=True)
p('')
center('Année Universitaire : ', bold=True)
p('')
p('')
center('MISE EN PLACE D’UN ERP COMMERCIAL MULTI-TENANT (MIHAJA_ERP_PRO) :',
       bold=True, size=14)
center('GESTION DES VENTES, DES STOCKS, DE LA COMPTABILITÉ, DE LA LIVRAISON '
       'ET DE LA RESSOURCE HUMAINE AVEC MARKETPLACE PUBLIQUE, ABONNEMENTS '
       'PAR ENTREPRISE ET RÔLE SUPER ADMIN PRIVÉ', bold=True, size=14)
page_break()

# ================================================================
# CURRICULUM VITAE (état civil laissé VIDE à compléter)
# ================================================================
center('CURRICULUM VITAE', bold=True, size=13)
p('')
p('ETAT CIVIL', bold=True)
p('Nom : ')
p('Prénom : ')
p('Date et lieu de naissance : ')
p('Situation familiale : ')
p('Adresse : ')
p('Email : ')
p('Numéro téléphone : ')
p('')
p('DIPLOMES OBTENUS : ', bold=True)
p('')
p('')
p('')
p('FORMATIONS ET EXPERIENCES PROFESSIONNELLES : ', bold=True)
p('')
p('')
page_break()

center('CONNAISSANCES INFORMATIQUES : ', bold=True)
p('Bureautique : Word, Excel, PowerPoint')
p('Développement de site Web : HTML, CSS, JavaScript, React JS')
p('Développement Backend : Python, Flask, Flask-RESTx, SQLAlchemy')
p('Langage de programmation : Python, JavaScript, SQL')
p('Environnement de développement : Visual Studio Code, Node.js, npm')
p('Système de Base de données : SQLite, PostgreSQL, MySQL')
p('Test et documentation API : pytest, Swagger, Postman')
p('Développement Desktop : Electron JS')
p('Système d’exploitation : Microsoft Windows (7, 8, 10, 11), Linux (Ubuntu)')
p('')
p('CONNAISSANCES LINGUISTIQUES : ', bold=True)
p('MALAGASY        Langue Maternelle')
p('FRANCAIS        Lu        Ecrit        Parlé')
p('ANGLAIS         Lu        Ecrit        Parlé')
p('')
p('PERSONNALITES : ', bold=True)
p('- Ayant l’esprit d’analyse, créatif, dévoué, dynamique')
p('- Personne responsable')
p('- Personne à forte motivation')
page_break()

# ================================================================
# AVANT PROPOS
# ================================================================
p('AVANT PROPOS', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=13)
p('')
p('En vue du passage en 3ème année, tous les étudiants de l’École de '
  'Management et d’Innovation Technologique (EMIT) en 2ème année doivent '
  'effectuer un stage de deux mois au sein d’une entreprise et réaliser un '
  'projet durant cette période. À l’issue du stage, chaque étudiant prépare '
  'une soutenance afin de présenter son thème. C’est au cours de ce stage '
  'que le présent rapport, en vue du passage en classe supérieure, est rédigé.')
p('Cet ouvrage a pour objet la mise en place d’un ERP (Enterprise Resource '
  'Planning) commercial multi-tenant dénommé MIHAJA_ERP_PRO, une plateforme '
  'de gestion commerciale couvrant les ventes, les stocks, les clients, les '
  'fournisseurs, la comptabilité, les ressources humaines, la livraison, les '
  'documents et les achats, complétée par une marketplace publique, un '
  'système d’abonnements par entreprise et un rôle Super Admin privé. Il '
  'présente également l’environnement du stage et l’établissement de '
  'formation. L’objectif de ce stage est de renforcer et de consolider les '
  'connaissances acquises durant la formation dispensée par l’école.')
p('Dans ce travail, nous allons utiliser le langage Python avec le '
  'micro-framework Flask côté serveur, le langage JavaScript avec la '
  'bibliothèque React côté client, et Electron pour la version desktop.')
page_break()

# ================================================================
# DEDICACES (laissée VIDE)
# ================================================================
center('DEDICACES', bold=True, size=13)
p('')
p('')
p('')
page_break()

# ================================================================
# REMERCIEMENTS (entreprise d'accueil laissée VIDE)
# ================================================================
center('REMERCIEMENTS', bold=True, size=13)
p('')
p('Avant tout développement de cette expérience professionnelle, il nous '
  'apparaît opportun de commencer ce rapport par des remerciements, que nous '
  'adressons à toutes les personnes qui nous ont apporté leur aide et qui '
  'ont contribué à l’élaboration de ce projet.')
p('Nous tenons à remercier sincèrement l’ensemble du personnel de '
  'l’entreprise d’accueil pour leur accueil chaleureux, leur disponibilité '
  'et leurs conseils précieux tout au long de la durée du stage.')
p('Nous remercions également, en la personne de :')
p('')
p('')
p('- Tous les enseignants de l’EMIT pour la qualité de la formation reçue,')
p('- Monsieur l’Évaluateur et tous les membres du jury pour avoir accepté '
  'd’évaluer ce rapport de stage,')
p('Enfin, à mes parents et aux membres de ma famille pour leurs sacrifices '
  'et leur soutien moral et financier tout au long de mes études, ainsi qu’à '
  'mes amis et à toutes les personnes qui m’ont aidé dans l’accomplissement '
  'de ce travail.')
page_break()
# ================================================================
# LISTE DES FIGURES
# ================================================================
center('LISTE DES FIGURES', bold=True, size=13)
p('')
for fig in [
    'figure 1- 1 : Organigramme de l’EMIT Fianarantsoa',
    'figure 1- 2 : Membres du bureau EMIT Fianarantsoa',
    'figure 2- 1 : Organigramme de l’entreprise d’accueil',
    'figure 2- 2 : Dirigeants de l’entreprise d’accueil',
    'figure 4- 1 : Cycle de la méthode Merise',
    'figure 6- 1 : Formalisme MCD',
    'figure 6- 2 : Modèle Conceptuel des Données (MCD) de l’application',
    'figure 6- 3 : Modèle Logique des Données (MLD) de l’application',
    'figure 6- 4 : Modèle Conceptuel des Traitements (MCT)',
    'figure 8- 1 : Architecture logicielle de l’application',
    'figure 8- 2 : Architecture matérielle de l’application',
    'figure 9- 1 : Page de connexion',
    'figure 9- 2 : Menu principal (Dashboard)',
    'figure 9- 3 : Page Produits',
    'figure 9- 4 : Page Ventes',
    'figure 9- 5 : Page Stocks',
    'figure 9- 6 : Marketplace publique',
    'figure 9- 7 : Interface Super Admin',
    'figure 9- 8 : Application Desktop (Electron)',
]:
    p(fig)
page_break()

# ================================================================
# LISTE DES TABLEAUX
# ================================================================
center('LISTE DES TABLEAUX', bold=True, size=13)
p('')
for tab in [
    'table 1- 1 : Tableau récapitulatif des mentions et parcours de l’EMIT',
    'table 3- 1 : Répartition du temps',
    'table 6- 1 : Dictionnaire des données de l’application',
    'table 7- 1 : Comparaison Flask / Laravel / Django',
    'table 7- 2 : Comparaison React / Angular / Vue',
    'table 7- 3 : Comparaison des SGBD (SQLite / MySQL / PostgreSQL)',
]:
    p(tab)
page_break()

# ================================================================
# LISTE DES ABREVIATIONS
# ================================================================
center('LISTE DES ABBREVIATIONS', bold=True, size=13)
p('')
for ab, desc in [
    ('API', 'Application Programming Interface (interface de programmation applicative)'),
    ('CRUD', 'Create, Read, Update, Delete (opérations de base sur les données)'),
    ('D.A.2.I', 'Développement d’Application Intranet-Internet'),
    ('EMIT', 'Ecole de Management et d’Innovation Technologique'),
    ('ERP', 'Enterprise Resource Planning (progiciel de gestion intégré)'),
    ('HTTP', 'HyperText Transfer Protocol'),
    ('HTTPS', 'HyperText Transfer Protocol Secure'),
    ('IA', 'Intelligence Artificielle'),
    ('JWT', 'JSON Web Token (jeton d’authentification)'),
    ('LMD', 'Licence, Master, Doctorat'),
    ('MCD', 'Modèle Conceptuel des Données'),
    ('MCT', 'Modèle Conceptuel des Traitements'),
    ('MLD', 'Modèle Logique des Données'),
    ('MPD', 'Modèle Physique des Données'),
    ('MERISE', 'Méthode d’Étude et de Réalisation Informatique pour les Systèmes d’Entreprise'),
    ('ORM', 'Object-Relational Mapping (mapping objet-relationnel)'),
    ('RBAC', 'Role-Based Access Control (contrôle d’accès basé sur les rôles)'),
    ('REST', 'Representational State Transfer (architecture d’API web)'),
    ('SGBD', 'Système de Gestion de Base de Données'),
    ('SQL', 'Structured Query Language'),
    ('UF', 'Université de Fianarantsoa'),
]:
    p(ab + ' : ' + desc)
page_break()

# ================================================================
# TABLE DE MATIERE (champ TOC Word)
# ================================================================
p('TABLE DE MATIERE', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=13)
p('')
add_toc()
page_break()

# ================================================================
# INTRODUCTION
# ================================================================
h(1, 'INTRODUCTION')
p('De nos jours, la gestion d’une entreprise exige de maîtriser en temps '
  'réel ses ventes, ses stocks, ses achats, sa comptabilité, ses ressources '
  'humaines et ses livraisons. Pourtant, de nombreuses entreprises gèrent '
  'encore ces activités de manière manuelle ou au moyen d’outils dispersés '
  '(carnets, fichiers Excel isolés, logiciels hétérogènes), ce qui engendre '
  'des erreurs, des pertes de temps et un manque de visibilité sur '
  'l’activité de l’entreprise.')
p('Face à cette problématique, le présent projet, intitulé « Mise en place '
  'd’un ERP commercial multi-tenant (MIHAJA_ERP_PRO) », consiste à concevoir '
  'et à développer une plateforme de gestion commerciale complète destinée '
  'aux entreprises. La solution est multi-tenant : chaque entreprise '
  '(tenant) dispose d’un environnement isolé soumis à un abonnement, tandis '
  'que le propriétaire de la plateforme dispose d’un rôle Super Admin privé '
  'pour gérer les tenants, les plans d’abonnement et les paiements. La '
  'plateforme propose également une marketplace publique où les entreprises '
  'abonnées publient leurs produits et où les clients simples peuvent '
  'commander en ligne.')
p('Ce rapport est structuré en trois parties. La première partie présente '
  'de manière générale l’école de formation, l’entreprise d’accueil et le '
  'projet. La deuxième partie est consacrée à l’analyse et à la conception '
  'du projet, en s’appuyant sur la méthode Merise. La troisième partie '
  'présente la réalisation de l’application : les outils utilisés, '
  'l’architecture et l’application développée. Une conclusion générale '
  'clôture le travail.')
page_break()

# ================================================================
# PARTIE I : PRESENTATION GENERALE
# ================================================================
center('PARTIE I : PRESENTATION GENERALE', bold=True, size=14)
p('')
page_break()

h(1, 'Chapitre 1 : PRESENTATION DE L’EMIT (Ecole de Management et '
     'd’Innovation Technologique)')
h(2, '1.1 Historique')
p('L’Ecole de Management et d’Innovation Technologique (EMIT) est un '
  'établissement public pluridisciplinaire, rattaché à l’Université de '
  'Fianarantsoa. Grâce à sa grande maturité dans l’enseignement et à la '
  'compétence de ses diplômés, les dirigeants, avec l’approbation du '
  'Ministère, ont décidé de convertir le Centre en École au sein de '
  'l’Université de Fianarantsoa par le Décret N°2016-1394 du 15 novembre '
  '2016.')
p('L’EMIT propose, d’une part, un diplôme de Master avec deux mentions et '
  'trois parcours, et d’autre part, un diplôme de Licence avec trois '
  'mentions et cinq parcours. Auparavant, elle était connue sous le nom de '
  'Centre Universitaire de Formation Professionnalisante (CUFP), créé par '
  'le Décret N°2005-205 du 26 avril 2005, et dispensait des diplômes de '
  'Licence professionnelle en Administration ainsi qu’en Informatique. '
  'Avant cela, elle était également connue sous le nom de Centre de '
  'Formation Continue (CFC), créé par l’Arrêté Rectoral N°99-23/UF/R du 10 '
  'mars 1999, qui formait des Techniciens Supérieurs.')
p('L’EMIT a été distinguée comme le « Meilleur Établissement » lors du '
  'Salon de la Recherche organisé par l’Organisation Internationale du '
  'Travail les 5 et 6 juillet 2017. Depuis l’année universitaire 2013-2014, '
  'l’école a entièrement adopté le système Licence, Master et Doctorat '
  '(LMD). Toutes les formations dispensées à l’EMIT sont habilitées par le '
  'Ministère de l’Enseignement Supérieur et de la Recherche Scientifique.')
h(2, '1.2 Mission de l’Ecole')
p('L’École a pour mission, d’abord, de dispenser des formations initiales '
  'et continues en informatique, en administration et en relation publiques. '
  'Ensuite, elle offre des services connexes à l’informatique et forme des '
  'techniciens supérieurs spécialisés, opérationnels immédiatement dans les '
  'entreprises. Elle assure le perfectionnement professionnel des '
  'étudiants, des demandeurs d’emplois, des employés et des cadres '
  'd’entreprises.')
h(2, '1.3 Organigramme de l’EMIT')
p('L’organigramme de l’École de Management et d’Innovation Technologique '
  'présente la structure organisationnelle de l’établissement. Il comprend '
  'différents conseils (conseil d’établissement, conseil scientifique), une '
  'direction, un collège des enseignants, des chefs de mention, ainsi que '
  'les services existants au sein de l’école.')
figure_placeholder('figure 1- 1 : Organigramme de l’EMIT Fianarantsoa')

h(2, '1.4 Partenaires')
p('L’EMIT travaille en collaboration avec plusieurs laboratoires de '
  'recherche, d’entreprises et d’autres écoles et universités. Parmi les '
  'organisations partenaires, citons à titre d’exemple les laboratoires de '
  'recherche tels que le LIMAD, LIMOS, IRD, CNRE, SPAD, Espace Dev, LRI et '
  'l’UPR-Green à travers le CIRAD. Pour ce qui est des écoles et des '
  'universités partenaires, il y a entre autres : l’EDMI, l’Université de '
  'Toulouse Paul Sabatier, l’Université de Montpellier 2, l’ENI, GOUVSOMU, '
  'IOGA, l’Université de Clermont Auvergne, ESMIA, l’Université de '
  'Mahajanga, l’ISSTM et l’Université de Fianarantsoa.')
p('L’école est également en partenariat avec plusieurs entreprises, '
  'notamment dans le cadre des stages à effectuer à travers chaque parcours, '
  'telles que les entreprises Etech consulting, Orange, Lazan’i Betsileo, '
  'STAR, Alliance Française de Fianarantsoa, AIRTEL Madagascar, ACCESS BANK '
  'Madagascar, Bank of Africa (BOA), BNI Madagascar, Manao, YAMAGOO, '
  'PREMIYA, JIRAMA, les assurances NY HAVANA, MAMA et ARO. Des organismes '
  'gouvernementaux sont également partenaires de l’EMIT : la Région Haute '
  'Matsiatra, le Ministère de l’Enseignement Supérieur et de la Recherche '
  'Scientifique, le Ministère de l’Education Nationale, le Ministère des '
  'Travaux Publics, le Ministère des Finances et du Budget, le Ministère du '
  'Tourisme, le Ministère des Transports et de la Météorologie, le Ministère '
  'de la Poste, de la Télécommunication et des Technologies Numériques, la '
  'Banque Centrale de Madagascar, le Foibe Taosaritanin’i Madagasikara '
  '(FTM) et l’INSTAT.')

h(2, '1.5 Cycle de licence')
p('Pour le cycle Licence, l’EMIT propose trois mentions, chacune subdivisée '
  'en parcours. Tous les étudiants de première année de Licence ont la '
  'possibilité d’effectuer un voyage d’études d’insertion en entreprise. À '
  'la fin de la deuxième année, chaque étudiant doit réaliser un stage et '
  'soutenir un rapport de stage. De plus, un stage suivi d’une soutenance '
  'de mémoire est exigé à la fin de la troisième année.')
caption('table 1- 1 : Tableau récapitulatif des mentions et parcours')
table(
    ['Cycle', 'Management', 'Informatique', 'Relation Publique et Multimédia'],
    [
        ['Licence',
         'Administration Économique et Sociale',
         'Développement d’Application Internet et Intranet (DA2I)',
         'Communication Multimédia ; Conception, Intégration et Gestion des '
         'Systèmes d’Information ; Relations Publiques et Communication '
         'Organisationnelle'],
        ['Master',
         'Management Décisionnel ; Management d’Entreprises et Développement '
         'des affaires (MEDA)',
         'Système d’Information, Géomatique et Décision (SIGD) ; Modélisation '
         'et Ingénierie Informatique (M2I) ; Sciences des Données et '
         'Intelligence Artificielle (SDIA)',
         'Relations Publiques et Multimédia ; Communication Numérique et '
         'Management de Projet (CNMP)'],
    ],
)
h(2, '1.6 Vie étudiante')
p('La vie étudiante permet aux étudiants de développer de véritables '
  'qualités humaines, organisationnelles et solidaires en leur offrant '
  'plusieurs opportunités. Les activités associatives permettent de gagner '
  'une expérience pratique précieuse en dehors du cadre académique et de '
  'mettre en application les théories enseignées en cours dans des '
  'contextes réels. L’EMIT compte notamment une association sportive, un '
  'club de danse, un club de musique, un club des jeunes entrepreneurs, un '
  'English Club, une bibliothèque numérique et une offre de formation en '
  'ligne.')
page_break()

# ------------------------------------------------- Chapitre 2 (VIDE)
h(1, 'Chapitre 2 : PRESENTATION DE L’ENTREPRISE D’ACCUEIL')
h(2, '2.1 Historique')
p('')
p('')
p('')
p('')
p('')
h(2, '2.2 Mission de l’entreprise')
p('')
p('')
p('')
p('')
p('')
h(2, '2.3 Organigramme de l’entreprise')
p('')
figure_placeholder('figure 2- 1 : Organigramme de l’entreprise d’accueil')
p('')
p('')
h(2, '2.4 Partenaires')
p('')
p('')
p('')
p('')
p('')
h(2, '2.5 Dirigeants de l’entreprise')
p('')
figure_placeholder('figure 2- 2 : Dirigeants de l’entreprise d’accueil')
p('')
p('')
page_break()

# ------------------------------------------------- Chapitre 3 (rempli)
h(1, 'Chapitre 3 : PRESENTATION DU PROJET')
h(2, '3.1 Origine du projet')
p('')
p('')
p('')
p('')
p('')
h(2, '3.2 Problématique')
p('De nombreuses entreprises gèrent encore leurs ventes, leurs stocks, '
  'leurs achats, leur comptabilité, leurs ressources humaines et leurs '
  'livraisons de manière manuelle ou au moyen d’outils dispersés. Cette '
  'situation entraîne plusieurs difficultés :')
p('- erreurs de saisie et incohérences entre les données commerciales et '
  'comptables ;')
p('- absence de suivi en temps réel du stock et des seuils critiques ;')
p('- absence d’environnement commercial (marketplace) permettant à '
  'l’entreprise de présenter ses produits et de recevoir des commandes '
  'en ligne ;')
p('- absence d’un cadre commercial clair entre le fournisseur de la '
  'solution et les entreprises clientes (isolations des données, quotas, '
  'abonnements, paiements) ;')
p('- manque de visibilité pour le propriétaire de la plateforme sur '
  'l’activité des entreprises abonnées.')
p('Il faut donc un système d’information unifié, isolé par entreprise, '
  'couvrant l’ensemble des processus commerciaux et accessible à la fois '
  'via une application web et une application de bureau.')
h(2, '3.3 Objectif du projet')
p('Le projet MIHAJA_ERP_PRO vise à concevoir et à développer une '
  'plateforme de gestion commerciale complète destinée aux entreprises, '
  'offrant les fonctionnalités suivantes :')
p('- authentification sécurisée avec JSON Web Token (access + refresh) et '
  'contrôle d’accès basé sur les rôles (RBAC) ;')
p('- gestion multi-tenant : chaque entreprise dispose d’un environnement '
  'isolé (données, quotas d’utilisateurs, de produits et de clients) ;')
p('- gestion des produits, des stocks avec seuils d’alerte et critiques, '
  'des clients, des fournisseurs, des ventes et des achats ;')
p('- gestion de la comptabilité, des factures, des ressources humaines, '
  'des livraisons et des documents ;')
p('- marketplace publique : publication des produits des entreprises '
  'abonnées, catalogue public et commandes en ligne des clients simples ;')
p('- système d’abonnements : plans, paiements et gestion du statut du '
  'tenant ;')
p('- rôle Super Admin privé : gestion de la plateforme, des tenants, des '
  'plans et des paiements, avec un environnement distinct ;')
p('- génération de QR codes, codes-barres, factures PDF et exports Excel ;')
p('- notifications, websockets et outils d’analyse (régression linéaire, '
  'z-score) ;')
h(2, '3.4 Séparation des rôles')
p('La solution distingue clairement trois catégories d’acteurs :')
p('- le SUPER ADMIN : propriétaire de la plateforme, n’appartient à aucun '
  'tenant ; il gère les tenants, les plans d’abonnement et les paiements '
  'depuis son environnement distinct ;')
p('- l’employé d’une entreprise cliente : compte rattaché à un seul tenant '
  '(admin, manager, sales, stock, accountant, rh, livreur) ; il accède aux '
  'modules opérationnels selon son rôle et selon l’abonnement de son '
  'entreprise ;')
p('- le client simple (USER) : sans tenant ni abonnement ; il consulte le '
  'catalogue public et commande en ligne.')

h(2, '3.5 Concrétisation du projet')
p('Le projet est mené en plusieurs étapes successives, de l’analyse des '
  'besoins jusqu’à la mise en production, en passant par la conception, '
  'le développement de l’API et des interfaces, les tests et la '
  'documentation.')
p('Plan de réalisation :')
p('1. Analyse des besoins et étude de l’existant ;')
p('2. Conception (méthode Merise : dictionnaire des données, règles de '
  'gestion, MCD, MLD, MCT) ;')
p('3. Mise en place de la base de données et des modèles ;')
p('4. Développement de l’API REST (authentification, multi-tenant, '
  'modules métier) ;')
p('5. Développement de l’application web (29 pages), de la version desktop '
  '(Electron) et du panneau super-admin ;')
p('6. Tests (pytest, Factory-Boy, Faker) et corrections ;')
p('7. Documentation (README, Swagger, guides) et mise en production.')
caption('table 3- 1 : Répartition du temps')
table(
    ['N°', 'Phase', 'Durée (semaines)', 'Période'],
    [
        ['1', 'Analyse et conception', '2', ''],
        ['2', 'Base de données et modèles', '1', ''],
        ['3', 'Développement de l’API', '2', ''],
        ['4', 'Interfaces web, desk et super-admin', '2', ''],
        ['5', 'Tests et corrections', '1', ''],
        ['6', 'Documentation et mise en production', '1', ''],
        ['', 'TOTAL', '9', ''],
    ],
)
page_break()

# ================================================================
# PARTIE II : ANALYSE ET CONCEPTION DU PROJET
# ================================================================
center('PARTIE II : ANALYSE ET CONCEPTION DU PROJET', bold=True, size=14)
p('')
page_break()

h(1, 'Chapitre 4 : METHODE ET NOTATION UTILISEE')
p('Les besoins recueillis auprès des utilisateurs sont modélisés puis '
  'traduits en base de données via un SGBD. Pour la conception, nous '
  'utilisons une méthode d’étude du Système d’Information (SI) : la méthode '
  'MERISE (Méthode d’Étude et de Réalisation Informatique pour les Systèmes '
  'd’Entreprise). Elle vise à modéliser et concevoir des systèmes '
  'd’information de manière structurée et méthodique.')
h(2, '4.1 Méthode Merise en général')
p('La méthode MERISE date de 1978-1979, et fait suite à une consultation '
  'nationale lancée en 1977 par le ministère de l’Industrie dans le but de '
  'choisir des sociétés de conseil en informatique afin de définir une '
  'méthode de conception de systèmes d’information. Les deux principales '
  'sociétés ayant mis au point cette méthode sont le CTI (Centre Technique '
  'd’Informatique) chargé de gérer le projet, et le CETE (Centre d’Études '
  'Techniques de l’Équipement) implanté à Aix-en-Provence. Elle propose une '
  'approche de la conception séparant l’étude des données de celle des '
  'traitements, en avançant progressivement par niveaux. Chacun de ces '
  'niveaux a pour objectif principal de fournir un certain nombre de '
  'documents (MCD, MLD, MPD, MCT, MCTA, MOT, MOTA) permettant ainsi la '
  'synthèse textuelle d’un processus de réflexion. Ces documents sont '
  'indispensables à l’élaboration et à la concertation autour de tout '
  'projet informatique. La mise en place des modèles de traitements a non '
  'seulement pour but de définir les traitements à effectuer, mais '
  'également de valider les options prises lors de l’élaboration des '
  'modèles de données. Ainsi, la méthode Merise préconise, non pas '
  'd’effectuer l’analyse des données, puis ensuite celle des traitements, '
  'mais plutôt de mener en parallèle, à chaque niveau, l’analyse des '
  'données et celle des traitements.')
p('La méthode MERISE propose un cadre méthodologique bien défini pour la '
  'conception de systèmes d’information. Elle guide les concepteurs à '
  'travers différentes étapes, de la modélisation conceptuelle à la mise '
  'en œuvre physique, ce qui favorise une approche méthodique et organisée '
  'du développement.')
h(2, '4.2 Niveaux d’analyse')
h(3, '4.2.1 Niveau conceptuel')
p('Ce niveau correspond au Modèle Conceptuel des Données (MCD) et au '
  'Modèle Conceptuel des Traitements (MCT). Le MCD formalise les données '
  'utilisées par le système d’information : entités, associations, '
  'cardinalités et attributs, indépendamment de tout choix technique. Le '
  'MCT décrit les opérations du système de manière synchronisée, sans se '
  'soucier de l’organisation ou des choix matériels.')
h(3, '4.2.2 Niveau logique ou organisationnel')
p('Ce niveau traduit le MCD en Modèle Logique des Données (MLD) tenant '
  'compte des contraintes du SGBD choisi (tables, clés primaires, clés '
  'étrangères). Le Modèle Organisationnel des Traitements (MOT) décrit '
  'qui fait quoi, où et quand : acteurs, postes de travail et séquences '
  'd’opérations.')
h(3, '4.2.3 Niveau physique ou opérationnel')
p('Ce niveau correspond au Modèle Physique des Données (MPD), traduisant '
  'les choix techniques et décrivant la base de données réellement créée '
  'dans le SGBD (types exacts, index, contraintes). Le Modèle Opérationnel '
  'des Traitements (MOT) résume le MLD et le MPD à travers les deux '
  'fonctions essentielles : la mise à jour et la consultation.')
figure_placeholder('figure 4- 1 : Cycle de la méthode Merise')
h(2, '4.3 Justification du choix de Merise')
p('Nous avons opté pour la méthode Merise car elle offre la possibilité de '
  'modéliser les éléments constitutifs d’un Système d’Information de '
  'Gestion (SIG) : les données, les utilisateurs, les traitements, les '
  'procédures et les postes de travail. Elle permet en outre de mener en '
  'parallèle l’analyse des données et celle des traitements, ce qui est '
  'adapté à un projet couvrant de nombreux modules métier (ventes, stocks, '
  'comptabilité, RH, livraison, achats) tout en garantissant l’isolation '
  'des données par entreprise (multi-tenant).')
page_break()

h(1, 'Chapitre 5 : ANALYSE DE CONCEPTION')
h(2, '5.1 Analyse des besoins')
p('L\u2019analyse des besoins a permis d\u2019identifier les attentes des utilisateurs : g\u00e9rer les produits, les stocks avec seuils d\u2019alerte, les clients, les fournisseurs, les ventes, les achats, la comptabilit\u00e9, les ressources humaines, les livraisons et les documents, publier les produits sur une marketplace publique, g\u00e9rer les abonnements par entreprise et administrer la plateforme via un r\u00f4le Super Admin priv\u00e9.')
p('Besoins fonctionnels : authentification JWT avec r\u00f4les (RBAC), isolation des donn\u00e9es par tenant, CRUD sur tous les modules m\u00e9tier, catalogue public et commandes en ligne, plans d\u2019abonnement et paiements, g\u00e9n\u00e9ration de QR codes, factures PDF et exports Excel, notifications et websockets.')
p('Besoins non fonctionnels : s\u00e9curit\u00e9 (mots de passe hach\u00e9s, blocklist JWT, CORS), disponibilit\u00e9 (web + desktop), performance (pagination, index), tra\u00e7abilit\u00e9 (logs d\u2019audit), maintenabilit\u00e9 (architecture en couches : routes, services, mod\u00e8les).')
h(2, '5.2 Analyse de l\u2019existant')
p('Avant le projet, de nombreuses entreprises g\u00e8rent leurs activit\u00e9s de fa\u00e7on manuelle ou avec des outils dispers\u00e9s (carnets, fichiers Excel isol\u00e9s, logiciels h\u00e9t\u00e9rog\u00e8nes) : saisies redondantes, \u00e9carts de stock, facturation non fiabilis\u00e9e, absence de canal de vente en ligne et absence de cadre d\u2019abonnement entre le fournisseur de la solution et les entreprises clientes.')
p('Le nouveau syst\u00e8me informatis\u00e9 unifie ces processus dans une plateforme multi-tenant unique, accessible via le web et le bureau, avec une marketplace publique et un panneau super-admin distinct.')
h(1, 'Chapitre 6 : CONCEPTION DU PROJET')
h(2, '6.1 D\u00e9finition de la conception')
p('La conception consiste \u00e0 mod\u00e9liser le futur syst\u00e8me d\u2019information avant sa r\u00e9alisation : identifier les donn\u00e9es, formaliser les r\u00e8gles de gestion, construire le MCD puis le d\u00e9river en MLD, et d\u00e9crire les traitements (MCT, MOT).')
h(2, '6.2 Dictionnaire des donn\u00e9es')
p('Le dictionnaire recense les principales donn\u00e9es manipul\u00e9es par la plateforme (extrait) :')
caption('table 6- 1 : Dictionnaire des donn\u00e9es de l\u2019application (extrait)')
table(
    ['Donn\u00e9e', 'Signification', 'Type', 'R\u00e8gle'],
    [
        ['id_tenant', 'Identifiant de l\u2019entreprise cliente', 'N', 'Cl\u00e9 primaire, unique'],
        ['nom_entreprise', 'Raison sociale de l\u2019entreprise', 'AN', 'Obligatoire'],
        ['plan_abonnement', 'Plan souscrit par l\u2019entreprise', 'AN', 'Obligatoire'],
        ['id_user', 'Identifiant utilisateur', 'N', 'Cl\u00e9 primaire'],
        ['role', 'R\u00f4le : super_admin, admin, manager, sales, stock, accountant, rh, livreur, user', 'AN', 'Obligatoire'],
        ['id_produit', 'Identifiant produit', 'N', 'Cl\u00e9 primaire'],
        ['prix_produit', 'Prix de vente unitaire', 'N', 'Positif'],
        ['stock_actuel', 'Quantit\u00e9 disponible', 'N', '>= 0, alerte si < seuil'],
        ['id_vente', 'Identifiant de vente / commande', 'N', 'Cl\u00e9 primaire'],
        ['montant_total', 'Total TTC de la vente', 'N', 'Calcul\u00e9'],
        ['statut_commande', 'Brouillon, confirm\u00e9e, livr\u00e9e, annul\u00e9e', 'AN', 'Obligatoire'],
        ['id_facture', 'Identifiant facture', 'N', 'Cl\u00e9 primaire'],
        ['id_ecriture', 'Identifiant \u00e9criture comptable', 'N', 'Partie double'],
    ],
)
h(2, '6.3 R\u00e8gles de gestion')
p('RG2 : un produit appartient a un tenant ; son stock declenche une alerte sous le seuil.')
p('RG3 : une vente est rattachee a un client et a un tenant ; elle genere une facture et met a jour le stock.')
p('RG4 : toute ecriture comptable respecte la partie double (debit = credit).')
p('RG5 : seuls les produits des entreprises abonnees actives sont visibles sur la marketplace.')
p('RG6 : le Super Admin ne gere que la plateforme (tenants, plans, paiements).')
h(2, '6.4 Modele Conceptuel des Donnees (MCD)')
p('Le MCD formalise les entites (Tenant, Utilisateur, Produit, Stock, Client, Fournisseur, Vente, Achat, Facture, Ecriture, Employe, Livraison, Document, Abonnement, Paiement), leurs associations et leurs cardinalites.')
figure_placeholder('figure 6- 1 : Formalisme MCD')
figure_placeholder('figure 6- 2 : MCD de l application MIHAJA_ERP_PRO')
h(2, '6.5 Modele Logique des Donnees (MLD)')
p('Tenant(id_tenant, nom_entreprise, plan, statut) ; Utilisateur(id_user, #id_tenant, nom, email, role) ; Produit(id_produit, #id_tenant, nom, prix, stock, seuil) ; Vente(id_vente, #id_tenant, #id_client, total, statut) ; Facture(id_facture, #id_vente, numero, total).')
figure_placeholder('figure 6- 3 : MLD de l application')
h(2, '6.6 MCT et MOT')
p('Le MCT decrit les operations (inscription tenant, authentification, vente, commande marketplace, facture, livraison). Le MOT precise qui fait quoi, ou et quand.')
figure_placeholder('figure 6- 4 : MCT de l application')
caption('table 6- 2 : Procedures fonctionnelles (extrait)')
table(
    ['Acteur', 'Operation', 'Resultat'],
    [
        ['Super Admin', 'Valider tenant / paiement', 'Tenant actif'],
        ['Admin entreprise', 'Creer utilisateurs et produits', 'Catalogue disponible'],
        ['Vendeur', 'Enregistrer une vente', 'Facture + stock a jour'],
        ['Client simple', 'Commander sur marketplace', 'Commande en preparation'],
        ['Comptable', 'Saisir une ecriture', 'Journal equilibre'],
        ['Livreur', 'Cloturer une livraison', 'Commande livree'],
    ],
)
page_break()
center('PARTIE III : REALISATION DU PROJET', bold=True, size=14)
p('')
page_break()
h(1, 'Chapitre 7 : SPECIFICATION DES OUTILS')
p('Backend Python/Flask (REST, SQLAlchemy, JWT, SocketIO). Frontend JavaScript/React + Electron desktop.')
caption('table 7- 1 : Comparaison Flask / Django / Laravel')
table(
    ['Critere', 'Flask (choisi)', 'Django', 'Laravel'],
    [
        ['Apprentissage', 'Douce, modulaire', 'Rigide', 'Complet (PHP)'],
        ['Multi-tenant', 'Architecture libre', 'Imposee', 'Imposee'],
    ],
)
h(2, '7.3 SGBD')
p('SQLite en developpement, PostgreSQL en production (migrations Alembic), MySQL compatible via SQLAlchemy.')
caption('table 7- 3 : Comparaison SQLite / MySQL / PostgreSQL')
table(
    ['Critere', 'SQLite', 'MySQL', 'PostgreSQL'],
    [
        ['Installation', 'Fichier unique', 'Serveur requis', 'Serveur requis'],
        ['Concurrence', 'Limitee', 'Bonne', 'Excellente'],
        ['Usage projet', 'Dev / tests', 'Compatible', 'Production'],
    ],
)
p('Outils : VS Code, Node/npm, Python/pytest, Git/GitHub, Postman/Swagger, Electron.')
figure_placeholder('figure 7- 1 : Caracteristiques de l ordinateur utilise')
figure_placeholder('figure 7- 2 : Visual Studio Code')
page_break()
h(1, 'Chapitre 8 : MISE EN OEUVRE')
h(2, '8.1 Architecture logicielle')
p('Client web React + client desktop Electron consomment la meme API REST Flask ; services + SQLAlchemy + JWT/RBAC ; PostgreSQL/SQLite.')
figure_placeholder('figure 8- 1 : Architecture logicielle de l application')
h(2, '8.2 Architecture materielle')
p('Poste client <-> serveur Flask <-> base PostgreSQL. Fichiers PDF/Excel/QR servis par le backend.')
figure_placeholder('figure 8- 2 : Architecture materielle de l application')
h(2, '8.3 Extraits de code')
p('Exemple 1 : modele multi-tenant avec tenant_id indexe. Exemple 2 : route protegee JWT + RBAC. Exemple 3 : page React catalogue marketplace.')
page_break()
h(1, 'Chapitre 9 : PRESENTATION DE L APPLICATION')
p('Connexion JWT, Dashboard, Produits, Ventes, Stocks, Marketplace publique, Super Admin, Desktop Electron.')
figure_placeholder('figure 9- 1 : Page de connexion')
figure_placeholder('figure 9- 2 : Dashboard')
figure_placeholder('figure 9- 3 : Page Produits')
figure_placeholder('figure 9- 4 : Page Ventes')
figure_placeholder('figure 9- 5 : Page Stocks')
figure_placeholder('figure 9- 6 : Marketplace publique')
figure_placeholder('figure 9- 7 : Interface Super Admin')
figure_placeholder('figure 9- 8 : Application Desktop')
page_break()
h(1, 'CONCLUSION GENERALE')
p('Plateforme ERP multi-tenant complete : API Flask, 40+ pages React, Electron, marketplace, abonnements, Super Admin.')
p('Perspectives : IA, hors-ligne desktop, paiements mobiles.')
page_break()
h(1, 'BIBLIOGRAPHIE')
p('[1] Cours Systeme d Information : Merise. [2] Docs Flask/SQLAlchemy/JWT. [3] Docs React/Electron. [4] Docs PostgreSQL.')
h(1, 'WEBOGRAPHIE')
p('- Flask : https://flask.palletsprojects.com/ - React : https://react.dev/ - Electron : https://www.electronjs.org/')
page_break()
h(1, 'ANNEXE')
p('')
page_break()
h(1, 'RESUME')
p('Stage ERP multi-tenant MIHAJA_ERP_PRO : ventes, stocks, comptabilite, RH, livraison, marketplace, abonnements, Super Admin. Analyse + conception Merise + developpement.')
p('Mots-cles : ERP, multi-tenant, Flask, React, Electron, PostgreSQL, marketplace.')
h(1, 'ABSTRACT')
p('Multi-tenant ERP internship project with sales, inventory, accounting, HR, delivery, marketplace, subscriptions and Super Admin.')
p('Keywords: ERP, multi-tenant, Flask, React, Electron, PostgreSQL, marketplace.')
doc.save(OUT)
print('OK -> ' + OUT)

