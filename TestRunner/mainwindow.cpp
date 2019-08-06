#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QCheckBox>
#include <QDebug>
#include <QFile>
#include <QFileDialog>
#include <QMessageBox>
#include <QThread>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow),
    commandList(new CommandList(this)),
    commandTimer(new QTimer(this)),
    delay_msec(1500),
    connection(new StripConnection(this)),
    currentCommand(nullptr)
{
    ui->setupUi(this);
    ui->commandView->setModel(commandList);

    connect(
        commandTimer, &QTimer::timeout,
        this, QOverload<>::of(&MainWindow::on_command_timer_triggered)
    );

    connect(
        connection, SIGNAL(error(const QString &)),
        this, SLOT(on_connection_error(const QString &))
    );

    connect(
        connection, SIGNAL(success()),
        this, SLOT(on_command_success())
    );

    logMessage("Ready");
}

MainWindow::~MainWindow()
{
    delete commandList;
    delete commandTimer;
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
    commandList->loadFromJson(fileContents);
    emit commandList->layoutChanged();
    ui->commandView->resizeColumnsToContents();
}

void MainWindow::logMessage(const QString & msg)
{
    ui->logMessageBrowser->append(QString("[%1] %2")
                                  .arg(QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))
                                  .arg(msg));
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
        logMessage(QString("File \"%1\" loaded successfully").arg(fileName));

        updateProgressBar();
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
    Q_ASSERT(connection != nullptr);

    // If we're still waiting for an answer from the server, stop immediately
    if(currentCommand != nullptr)
        return;

    if (! connection->loggedIn) {
        try {
            connection->login();
            logMessage("Login request to the server");

            int retryCount{5};
            while (connection->commandRunning() && retryCount > 0) {
                QThread::msleep(100);
                --retryCount;
            }

            if(! connection->commandRunning()) {
                throw QString("Unable to get a login token from the server");
            } else {
                logMessage("Connection to the server has been established, good!");
            }
        }
        catch (const QString & errMsg) {
            QString msg = QString("Error connecting to the server: %1").arg(errMsg);
            logMessage(msg);
            QMessageBox::critical(this, "Error connecting to the server", errMsg);
            commandTimer->stop();
            return;
        }
    }

    int curIdx{0};

    // Look for the first command that has not been executed yet
    for (auto & curCommand : commandList->command_list) {
        if (curCommand.time.isNull()) {
            currentCommand = &curCommand;
            // This is the first command whose date has not been set yet: run it!
            logMessage(QString("Running command: %1")
                       .arg(commandToStr(curCommand)));

            if (! ui->dryRunCheckBox->isChecked()) {
                connection->send(curCommand.url, curCommand.parameters);
            } else {
                on_command_success();
            }

            return;
        }

        ++curIdx;
    }
}

void MainWindow::on_command_success()
{
    if(currentCommand != nullptr) {
        currentCommand->time = QDateTime::currentDateTime();
        currentCommand = nullptr;

        updateProgressBar();
    }
}

void MainWindow::on_connection_error(const QString & msg)
{
    logMessage(msg);
}

void MainWindow::on_runButton_clicked()
{
    if (commandTimer->isActive()) {
        commandTimer->stop();

        ui->runButton->setText(tr("&Run"));

        ui->runNextButton->setEnabled(true);
        logMessage("Command sequence paused");
    } else {
        ui->runNextButton->setEnabled(false);
        ui->runButton->setText(tr("&Stop"));

        commandTimer->start(delay_msec);
        logMessage("Command sequence started");
    }
}

void MainWindow::on_runNextButton_clicked()
{
    emit on_command_timer_triggered();
}

void MainWindow::updateProgressBar()
{
    ui->progressBar->setRange(0, commandList->command_list.length());

    int numOfCompletedCommands{0};
    for (auto & curCommand : commandList->command_list) {
        if (! curCommand.time.isNull()) {
            ++numOfCompletedCommands;
        }
    }
    ui->progressBar->setValue(numOfCompletedCommands);
}
