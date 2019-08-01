#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDebug>
#include <QFile>
#include <QFileDialog>
#include <QMessageBox>
#include <QThread>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow),
    command_list(new CommandList(this)),
    command_timer(new QTimer(this)),
    delay_msec(1500)
{
    ui->setupUi(this);
    ui->commandView->setModel(command_list);

    connect(
        command_timer, &QTimer::timeout,
        this, QOverload<>::of(&MainWindow::on_command_timer_triggered)
    );
}

MainWindow::~MainWindow()
{
    delete command_list;
    delete command_timer;
    delete ui;
}

void MainWindow::loadJsonFile(const QString & fileName)
{
    QFile inputFile(fileName);
    if (! inputFile.open(QFile::ReadOnly)) {
        throw QString("Unable to open file %1").arg(fileName);
    }

    QTextStream inp(&inputFile);
    QString fileContents = inp.readAll();
    command_list->loadFromJson(fileContents);
    emit command_list->layoutChanged();
    ui->commandView->resizeColumnsToContents();
}

void MainWindow::on_action_quit_triggered()
{
    close();
}

void MainWindow::on_action_load_triggered()
{
    auto fileName = QFileDialog::getOpenFileName(
                this,
                tr("Open command sequence"),
                "",
                tr("JSON file (*.json);; All files (*)")
    );
    if(fileName.isEmpty())
        return;

    try {
        loadJsonFile(fileName);
    }
    catch (const QString &errMsg) {
        QMessageBox::critical(
                    this,
                    QString("Error opening file \"%1\"").arg(fileName),
                    errMsg
        );
    }
}

void MainWindow::on_command_timer_triggered()
{
    // Look for the first command that has not been executed yet
    int curIdx{0};
    for (auto & curCommand : command_list->command_list) {
        if (curCommand.time.isNull()) {
            // This is the first command whose date has not been set yet: run it!
            qDebug() << curCommand;

            command_list->setCommandTime(curIdx, QDateTime::currentDateTime());
            return;
        }

        ++curIdx;
    }
}

void MainWindow::on_runButton_clicked()
{
    if (command_timer->isActive()) {
        command_timer->stop();

        ui->runButton->setText(tr("&Run"));

        ui->runNextButton->setEnabled(true);
    } else {
        ui->runNextButton->setEnabled(false);
        ui->runButton->setText(tr("&Stop"));

        command_timer->start(delay_msec);
    }
}

void MainWindow::on_runNextButton_clicked()
{
    emit on_command_timer_triggered();
}
