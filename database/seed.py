"""
Seed data script for the School Grades system.
Creates sample data for testing and demonstration.
"""
from datetime import datetime, timedelta
import random
from database import (
    get_db_context, init_db, 
    User, Disciplina, Turma, AlunoTurma, Avaliacao
)


def seed_database():
    """Populate database with sample data."""
    
    with get_db_context() as db:
        # Clear existing data
        db.query(Avaliacao).delete()
        db.query(AlunoTurma).delete()
        db.query(User).delete()
        db.query(Disciplina).delete()
        db.query(Turma).delete()
        
        # Create Teachers
        teachers = [
            User(name="Prof. Maria Silva", role="teacher"),
            User(name="Prof. João Santos", role="teacher"),
        ]
        db.add_all(teachers)
        db.flush()
        
        # Create Students
        students = [
            User(name="Miguel Ferreira", role="student"),
            User(name="Ana Costa", role="student"),
            User(name="Pedro Almeida", role="student"),
            User(name="Sofia Rodrigues", role="student"),
            User(name="João Oliveira", role="student"),
            User(name="Beatriz Martins", role="student"),
        ]
        db.add_all(students)
        db.flush()
        
        # Create Disciplinas (Subjects)
        disciplinas = [
            Disciplina(name="Matemática"),
            Disciplina(name="Português"),
            Disciplina(name="Inglês"),
            Disciplina(name="História"),
            Disciplina(name="Ciências"),
        ]
        db.add_all(disciplinas)
        db.flush()
        
        # Create Turmas (Classes)
        turmas = [
            Turma(name="10A"),
            Turma(name="10B"),
            Turma(name="11A"),
        ]
        db.add_all(turmas)
        db.flush()
        
        # Assign students to classes
        # First 3 students in 10A, next 2 in 10B, last one in 11A
        alunos_turmas = [
            AlunoTurma(user_id=students[0].id, turma_id=turmas[0].id),  # Miguel -> 10A
            AlunoTurma(user_id=students[1].id, turma_id=turmas[0].id),  # Ana -> 10A
            AlunoTurma(user_id=students[2].id, turma_id=turmas[0].id),  # Pedro -> 10A
            AlunoTurma(user_id=students[3].id, turma_id=turmas[1].id),  # Sofia -> 10B
            AlunoTurma(user_id=students[4].id, turma_id=turmas[1].id),  # João -> 10B
            AlunoTurma(user_id=students[5].id, turma_id=turmas[2].id),  # Beatriz -> 11A
        ]
        db.add_all(alunos_turmas)
        db.flush()
        
        # Create sample evaluations
        modulos = ["Módulo 1", "Módulo 2", "Módulo 3"]
        descricoes = ["Teste 1", "Teste 2", "Trabalho", "Projeto", "Ficha A"]
        
        avaliacoes = []
        base_date = datetime.now() - timedelta(days=90)
        
        for student in students:
            # Get student's turma
            aluno_turma = db.query(AlunoTurma).filter_by(user_id=student.id).first()
            if aluno_turma:
                # Create grades for each disciplina
                for disciplina in disciplinas[:3]:  # First 3 subjects
                    for i, modulo in enumerate(modulos[:2]):  # First 2 modules
                        for j, descricao in enumerate(descricoes[:2]):  # 2 evaluations per module
                            avaliacao = Avaliacao(
                                user_id=student.id,
                                disciplina_id=disciplina.id,
                                turma_id=aluno_turma.turma_id,
                                modulo=modulo,
                                descricao=descricao,
                                valor=round(random.uniform(10, 20), 1),  # Random grade 10-20
                                date=base_date + timedelta(days=random.randint(1, 80)),
                                updated_by=teachers[0].id,
                            )
                            avaliacoes.append(avaliacao)
        
        db.add_all(avaliacoes)
        db.commit()
        
        print("Database seeded successfully!")
        print(f"Created:")
        print(f"  - {len(teachers)} teachers")
        print(f"  - {len(students)} students")
        print(f"  - {len(disciplinas)} subjects")
        print(f"  - {len(turmas)} classes")
        print(f"  - {len(avaliacoes)} evaluations")
        
        # Print some IDs for reference
        print("\nReference IDs:")
        print(f"  Teachers: {[(t.id, t.name) for t in teachers]}")
        print(f"  Students: {[(s.id, s.name) for s in students]}")


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Seeding database...")
    seed_database()
