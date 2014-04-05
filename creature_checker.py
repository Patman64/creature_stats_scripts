#!/usr/bin/env python

"""
Written by Patman64.
"""

import MySQLdb as mysql

DB_INFO = {
        'db': 'freebird_world_stats',
      'host': 'localhost',
      'user': 'root',
    'passwd': ''
}

OUTPUT_FILE = 'creature_report.txt'
ACCURACY = 1

creature_count = 0
defect_count = 0

RANKS = ['Normal', 'Elite', 'Rare Elite', 'World Boss', 'Rare']
UNIT_CLASSES = ['???', 'Warrior', 'Paladin', '', 'Rogue', '', '', '', 'Mage']
MAX_LEVEL = 65

TESTS = [
    ('Check that all warriors have no mana.',
        'UnitClass = 1 and (MinLevelMana != 0 or MaxLevelMana != 0)'),

    ('Check that all non-warriors have mana.',
        'UnitClass != 1 and (MinLevelMana = 0 or MaxLevelMana = 0)'),

    ('Check that no creatures have health multiplier = 0.',
        'HealthMultiplier = 0'),

    ('Check that no creatures have mana multiplier = 0.',
        'ManaMultiplier = 0'),

    ('Check that all creatures have a valid rank (0-4).',
        'Rank < 0 or Rank > 4'),
]

def main(cursor):
    print 'Loading creature stats...'
    cursor.execute("""
        SELECT Level, Class, BaseMana, BaseHealthExp0
        FROM creature_template_classlevelstats""")

    stats = {}
    for row in cursor.fetchall():
        Level, Class = row[0], row[1]
        if not Class in stats: stats[Class] = {}
        stats[Class][Level] = dict(
            BaseMana=row[2],
            BaseHealthExp0=row[3])

    print '\nChecking creatures...'
    cursor.execute("""
        SELECT entry, name, minlevel, maxlevel, minlevelhealth, maxlevelhealth, Rank,
        minlevelmana, maxlevelmana, unitclass, healthmultiplier, manamultiplier
        FROM creature_template""")

    with open(OUTPUT_FILE, 'w') as f:
        for row in cursor.fetchall():
            global creature_count
            creature_count += 1
            check_creature(f, stats, *row)

        percent = float(defect_count)/creature_count*100
        if percent > 99.99 and percent < 100: percent = 99.99
        print 'Out of {0} creatures, {1} were defective ({2:.2f}%).'\
            .format(creature_count, defect_count, percent)

        f.write('=============================================================\n\n')
        f.write('Test results:\n')
        print '\nPerforming tests...'

        for test in TESTS:
            rows = cursor.execute('SELECT * FROM creature_template WHERE ' + test[1])
            if rows == 0:
                print 'Pass! ' + test[0]
                f.write('Pass! ' + test[0] + '\n')
            else:
                print 'FAIL! ({} results) '.format(rows) + test[0]
                f.write('FAIL! ({} results) '.format(rows) + test[0] + '\n')

    print '\nFull report saved to: ' + OUTPUT_FILE

def check_creature(out, stats, entry, name, l_level, h_level, l_health, h_health, rank,
    l_mana, h_mana, unit_class, health_mult, mana_mult):

    assert l_level >= 1, 'Min level {} is less than 1!'.format(l_level)
    assert h_level <= MAX_LEVEL, 'Max level {} is greater than {}!'.format(h_level, MAX_LEVEL)

    def within_range(a, b):
        return abs(a - b) <= ACCURACY

    if unit_class != 0:
        l_stats, h_stats = stats[unit_class][l_level], stats[unit_class][h_level]

        l_health_calc = l_stats['BaseHealthExp0'] * health_mult
        h_health_calc = h_stats['BaseHealthExp0'] * health_mult
        bad_health = False
        inconsistent_health = False

        if not within_range(l_health, l_health_calc) or not within_range(h_health, h_health_calc):
            bad_health = True
            health_mult_calc = float(l_health) / l_stats['BaseHealthExp0']

            if not within_range(int(float(h_health) / h_stats['BaseHealthExp0']), int(health_mult_calc)):
                inconsistent_health = True
            
        l_mana_calc = l_stats['BaseMana'] * mana_mult
        h_mana_calc = h_stats['BaseMana'] * mana_mult
        bad_mana = False
        inconsistent_mana = False

        if not within_range(l_mana, l_mana_calc) or not within_range(h_mana, h_mana_calc):
            bad_mana = True

            if l_stats['BaseMana'] == 0:
                inconsistent_mana = True
            else:
                mana_mult_calc = float(l_mana) / l_stats['BaseMana']
                
                if not within_range(int(float(h_mana) / h_stats['BaseMana']), int(mana_mult_calc)):
                    inconsistent_mana = True

    def make_suggestions(multiplier_calc, health=False, mana=False):
        suggestions = []
        classes = [1, 2, 8]
        for _class in classes:
            l_stats, h_stats = stats[_class][l_level], stats[_class][h_level]
            if health:
                _l_health_calc = l_stats['BaseHealthExp0'] * health_mult
                _h_health_calc = h_stats['BaseHealthExp0'] * health_mult

                if within_range(l_health, _l_health_calc) and within_range(h_health, _h_health_calc):
                    suggestions.append('change class to ' + str(_class))
            elif mana:
                _l_mana_calc = l_stats['BaseMana'] * mana_mult
                _h_mana_calc = h_stats['BaseMana'] * mana_mult

                if within_range(l_mana, _l_mana_calc) and within_range(h_mana, _h_mana_calc):
                    suggestions.append('change class to ' + str(_class))

        if multiplier_calc > 0:
            suggestions.append('change multiplier to {:.4f}'.format(multiplier_calc))
        else:
            suggestions.append('no multiplier possible (data inconsistent)')

        return suggestions

    if unit_class == 0 or bad_health or bad_mana:
        global defect_count
        defect_count += 1

        out.write('=============================================================\n')
        out.write('\n')
        out.write('DATABASE\n')

        def write_field(field, value):
            out.write('  {0:12} {1:<}\n'.format(field.capitalize() + ':', value))

        write_field('name', name)
        write_field('entry', entry)
        out.write('  {0:12} {1:<} ({2})\n'.format('Class:', unit_class, UNIT_CLASSES[unit_class]))
        out.write('  {0:12} {1:<} ({2})\n'.format('Rank:', rank, RANKS[rank]))
        write_field('min level', l_level)
        write_field('max level', h_level)

        if unit_class != 0:
            write_field('min health', l_health)
            write_field('max health', h_health)
            write_field('min mana', l_mana)
            write_field('max mana', h_mana)
            write_field('health mult', health_mult)
            write_field('mana mult', mana_mult)
            out.write('\n')

            out.write('CALCULATED VALUES\n')
            write_field('min health', l_health_calc)
            write_field('max health', h_health_calc)
            write_field('min mana', l_mana_calc)
            write_field('max mana', h_mana_calc)
            out.write('\n')

            if bad_health:
                out.write('ERROR: Health values does not match.\n')
                out.write('Suggestions:\n')
                for suggestion in make_suggestions(0 if inconsistent_health else health_mult_calc, health=True):
                    out.write(' - {}.\n'.format(suggestion.capitalize()))
                out.write('\n')

            if bad_mana:
                out.write('ERROR: Mana values does not match.\n')
                out.write('Suggestions:\n')
                for suggestion in make_suggestions(0 if inconsistent_mana else mana_mult_calc, mana=True):
                    out.write(' - {}.\n'.format(suggestion.capitalize()))
                out.write('\n')

        else:
            out.write('\n\nNo class given in database.\n')

            out.write('Suggestions based on health:\n')
            for suggestion in make_suggestions(0, health=True):
                out.write(' - {}.\n'.format(suggestion.capitalize()))
            out.write('\n')

            out.write('Suggestions based on mana:\n')
            for suggestion in make_suggestions(0, mana=True):
                out.write(' - {}.\n'.format(suggestion.capitalize()))
            out.write('\n')

if __name__ == '__main__':
    connection = mysql.connect(**DB_INFO)
    try:
        cursor = connection.cursor()
        main(cursor)
    finally:
        connection.close()