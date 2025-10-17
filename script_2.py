from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# Configuration de la base de données
def get_db_connection():
    conn = psycopg2.connect("postgres://avnadmin:AVNS_JVms0OTZ9dva2FMpes9@srm-20rsk25-aitbelaid-1024.d.aivencloud.com:26207/defaultdb?sslmode=require")
    return conn

@app.route('/')
def home():
    return render_template('index.html')

# Route pour les statistiques
@app.route('/stats')
def stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Statistiques par métier
    query_metiers = """
        SELECT 
            m.nom_metier,
            COUNT(d.id_donnee) as nombre_releves,
            SUM(d.linear_estime) as total_linear,
            ROUND(AVG(k.taux_avancement_global), 2) as taux_avancement_moyen
        FROM Metiers m
        LEFT JOIN DonneesCollectees d ON m.id_metier = d.id_metier
        LEFT JOIN IndicateursKPI k ON m.id_metier = k.id_metier
        GROUP BY m.id_metier, m.nom_metier
    """
    cursor.execute(query_metiers)
    stats_metiers = cursor.fetchall()
                
    # Statistiques par centre
    query_centres = """
        SELECT 
            c.nom_centre,
            c.direction_provinciale,
            COUNT(d.id_donnee) as nombre_releves,
            SUM(d.linear_estime) as total_linear
        FROM Centres c
        LEFT JOIN DonneesCollectees d ON c.id_centre = d.id_centre
        GROUP BY c.id_centre, c.nom_centre, c.direction_provinciale
        ORDER BY total_linear DESC
    """
    cursor.execute(query_centres)
    stats_centres = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('stats.html', stats_metiers=stats_metiers, stats_centres=stats_centres)

# Route pour la saisie des données
@app.route('/saisie')
def saisie():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer les données pour les menus déroulants
    cursor.execute("SELECT id_centre, nom_centre, direction_provinciale FROM Centres WHERE statut_centre = 'actif'")
    centres = cursor.fetchall()
    
    cursor.execute("SELECT id_metier, nom_metier FROM metiers")
    metiers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('saisie.html', centres=centres, metiers=metiers)

# API pour récupérer les types de réseau basés sur le métier
@app.route('/api/types_reseau/<int:id_metier>')
def get_types_reseau(id_metier):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id_type_reseau, nom_type_reseau 
        FROM typesreseau 
        WHERE id_metier = %s
    """, (id_metier,))
    
    types_reseau = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convertir en format JSON
    result = [{'id_type_reseau': row[0], 'nom_type_reseau': row[1]} for row in types_reseau]
    return jsonify(result)

# Route pour ajouter un centre
@app.route('/add_centre')
def add_centre():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer les centres existants
    cursor.execute("""
        SELECT id_centre, nom_centre, direction_provinciale, territoire, telephone, responsable_centre, statut_centre, date_creation
        FROM Centres
        ORDER BY date_creation DESC
    """)
    centres = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('add_centre.html', centres=centres)

# Route pour sauvegarder un centre
@app.route('/sauvegarder_centre', methods=['POST'])
def sauvegarder_centre():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les données du formulaire
        data = {
            'nom_centre': request.form.get('nom_centre'),
            'direction_provinciale': request.form.get('direction_provinciale'),
            'territoire': request.form.get('territoire'),
            'date_creation': request.form.get('date_creation'),
            'telephone': request.form.get('telephone') or None,
            'responsable_centre': request.form.get('responsable_centre'),
            'statut_centre': request.form.get('statut_centre', 'actif')
            
        }
        
        # Requête d'insertion
        query = """
        INSERT INTO Centres (
            nom_centre, direction_provinciale, territoire, date_creation, telephone, responsable_centre, statut_centre
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            data['nom_centre'], data['direction_provinciale'], data['territoire'],
            data['date_creation'], data['telephone'], data['responsable_centre'], data['statut_centre']
        )
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Centre ajouté avec succès!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Route pour sauvegarder les données
@app.route('/sauvegarder_donnee', methods=['POST'])
def sauvegarder_donnee():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les données du formulaire
        data = {
            'id_centre': request.form.get('centre'),
            'id_metier': request.form.get('metier'),
            'id_type_reseau': request.form.get('type_reseau'),
            'statut_integration': request.form.get('statut_integration', 'en_attente'),
            'linear_theorique': request.form.get('linear_theorique') or None,
            'linear_estime': request.form.get('linear_estime') or None,
            'linear_integrable': request.form.get('linear_integrable') or None,
            'linear_semi_integrable': request.form.get('linear_semi_integrable') or None,
            'linear_a_collecter': request.form.get('linear_a_collecter') or None,
            'nombre_ouvrages': request.form.get('nombre_ouvrages') or None,
            'ouvrages_integrables': request.form.get('ouvrages_integrables') or None,
            'ouvrages_a_traiter': request.form.get('ouvrages_a_traiter') or None,
            'ouvrages_a_collecter': request.form.get('ouvrages_a_collecter') or None,
            'source_donnee': request.form.get('source_donnee', ''),
            'format_donnee': request.form.get('format_donnee', ''),
            'annee_reference': request.form.get('annee_reference') or None,
            'precision_estimee': request.form.get('precision_estimee') or None,
            'date_collecte': request.form.get('date_collecte'),
            'agent_collecteur': request.form.get('agent_collecteur', ''),
            'notes': request.form.get('notes', '')
        }
        
        # Requête d'insertion
        query = """
        INSERT INTO DonneesCollectees (
            id_centre, id_metier, id_type_reseau, statut_integration,
            linear_theorique, linear_estime, linear_integrable, 
            linear_semi_integrable, linear_a_collecter,
            nombre_ouvrages, ouvrages_integrables, ouvrages_a_traiter, ouvrages_a_collecter,
            source_donnee, format_donnee, annee_reference, precision_estimee,
            date_collecte, agent_collecteur, notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            data['id_centre'], data['id_metier'], data['id_type_reseau'], data['statut_integration'],
            data['linear_theorique'], data['linear_estime'], data['linear_integrable'],
            data['linear_semi_integrable'], data['linear_a_collecter'],
            data['nombre_ouvrages'], data['ouvrages_integrables'], data['ouvrages_a_traiter'], data['ouvrages_a_collecter'],
            data['source_donnee'], data['format_donnee'], data['annee_reference'], data['precision_estimee'],
            data['date_collecte'], data['agent_collecteur'], data['notes']
        )
        
        cursor.execute(query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Donnée sauvegardée avec succès!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
   app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
